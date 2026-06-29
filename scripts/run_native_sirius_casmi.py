#!/usr/bin/env python3
"""Generate native SIRIUS 4.9 formula scores for CASMI2022 spectra.

The script runs the local headless SIRIUS 4.9.15 CLI in offline formula mode,
parses formula_candidates.tsv, and writes query-level formula scores. It does
not use fallback scoring and does not force the true formula into SIRIUS.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIRIUS = Path('/home/zhome/opt/sirius-4.9.15-headless/bin/sirius')
DEFAULT_CASMI = ROOT / 'data' / 'proc' / 'casmi_2022'
OUTDIR = ROOT / 'results' / 'native_sirius_casmi'


def safe_text(value: Any) -> str:
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except Exception:
        pass
    return str(value)


def parse_peaks(peaks: Any) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for peak in peaks or []:
        try:
            mz, intensity = peak
            out.append((float(mz), float(intensity)))
        except Exception:
            continue
    if not out:
        return out
    max_i = max(i for _, i in out) or 1.0
    return [(mz, 100.0 * i / max_i) for mz, i in out]


def write_mgf(spec_df: pd.DataFrame, path: Path) -> None:
    with path.open('w', encoding='utf-8') as handle:
        for _, row in spec_df.iterrows():
            spec_id = safe_text(row.get('spec_id'))
            adduct = safe_text(row.get('prec_type')) or '[M+?]+'
            charge = '1-' if '-' in adduct else '1+'
            ion_mode = 'negative' if '-' in adduct or safe_text(row.get('ion_mode')).upper().startswith('N') else 'positive'
            handle.write('BEGIN IONS\n')
            handle.write(f'TITLE=CASMI_SPEC_{spec_id}\n')
            handle.write(f'SCANS={spec_id}\n')
            handle.write(f'PEPMASS={float(row.get("prec_mz")):.8f}\n')
            handle.write(f'CHARGE={charge}\n')
            handle.write('MSLEVEL=2\n')
            handle.write(f'IONMODE={ion_mode}\n')
            handle.write(f'ADDUCT={adduct}\n')
            for mz, intensity in parse_peaks(row.get('peaks')):
                handle.write(f'{mz:.6f} {intensity:.6f}\n')
            handle.write('END IONS\n\n')


def parse_candidates(project: Path) -> pd.DataFrame:
    rows = []
    for tsv in project.glob('*/formula_candidates.tsv'):
        dirname = tsv.parent.name
        match = re.search(r'CASMI_SPEC_(\d+)', dirname)
        if not match:
            # Fall back to compound.info when directory naming changes.
            info = tsv.parent / 'compound.info'
            text = info.read_text(errors='ignore') if info.exists() else ''
            match = re.search(r'CASMI_SPEC_(\d+)', text)
        if not match:
            continue
        spectrum_id = match.group(1)
        try:
            df = pd.read_csv(tsv, sep='\t')
        except Exception as exc:
            rows.append({
                'spectrum_id': spectrum_id,
                'candidate_formula': '',
                'sirius_native_formula_score_raw': math.nan,
                'sirius_native_formula_rank': math.nan,
                'sirius_native_status': 'parse_failed',
                'error_message': repr(exc),
                'sirius_source_file': str(tsv),
            })
            continue
        if df.empty:
            rows.append({
                'spectrum_id': spectrum_id,
                'candidate_formula': '',
                'sirius_native_formula_score_raw': math.nan,
                'sirius_native_formula_rank': math.nan,
                'sirius_native_status': 'no_formula_candidates',
                'error_message': '',
                'sirius_source_file': str(tsv),
            })
            continue
        score_col = 'SiriusScore' if 'SiriusScore' in df.columns else 'TreeScore'
        for _, row in df.iterrows():
            rows.append({
                'spectrum_id': spectrum_id,
                'candidate_formula': safe_text(row.get('molecularFormula')),
                'sirius_native_formula_score_raw': row.get(score_col, math.nan),
                'sirius_native_formula_rank': row.get('rank', math.nan),
                'sirius_native_status': 'available',
                'error_message': '',
                'sirius_source_file': str(tsv),
            })
    return pd.DataFrame(rows)


def normalize_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df['sirius_native_formula_score'] = []
        return df
    df['sirius_native_formula_score_raw'] = pd.to_numeric(df['sirius_native_formula_score_raw'], errors='coerce')
    norm_rows = []
    for spectrum_id, group in df.groupby('spectrum_id', dropna=False):
        group = group.copy()
        avail = group[group['sirius_native_status'].eq('available') & group['sirius_native_formula_score_raw'].notna()]
        if avail.empty:
            group['sirius_native_formula_score'] = math.nan
        else:
            mn = avail['sirius_native_formula_score_raw'].min()
            mx = avail['sirius_native_formula_score_raw'].max()
            if mx == mn:
                group['sirius_native_formula_score'] = group['sirius_native_formula_score_raw'].map(lambda x: 1.0 if pd.notna(x) else math.nan)
            else:
                group['sirius_native_formula_score'] = (group['sirius_native_formula_score_raw'] - mn) / (mx - mn)
        norm_rows.append(group)
    return pd.concat(norm_rows, ignore_index=True)



def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--casmi-dir', default=str(DEFAULT_CASMI))
    parser.add_argument('--sirius-bin', default=str(DEFAULT_SIRIUS))
    parser.add_argument('--cores', type=int, default=4)
    parser.add_argument('--candidates', type=int, default=10)
    parser.add_argument('--compound-timeout', type=int, default=90)
    parser.add_argument('--max-spectra', type=int, default=0)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    outdir = OUTDIR
    logdir = outdir / 'logs'
    single_dir = outdir / 'single_inputs'
    project_root = outdir / 'sirius_project_single'
    outdir.mkdir(parents=True, exist_ok=True)
    logdir.mkdir(parents=True, exist_ok=True)
    single_dir.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)

    spec_path = Path(args.casmi_dir) / 'spec_df.pkl'
    if not spec_path.exists():
        raise SystemExit(f'CASMI spec_df.pkl not found: {spec_path}')
    sirius_bin = Path(args.sirius_bin)
    if not sirius_bin.exists():
        raise SystemExit(f'SIRIUS executable not found: {sirius_bin}')

    spec_df = pd.read_pickle(spec_path)
    if args.max_spectra > 0:
        spec_df = spec_df.head(args.max_spectra).copy()
    combined_mgf = outdir / 'casmi2022_sirius_input.mgf'
    write_mgf(spec_df, combined_mgf)

    formula_csv = outdir / 'casmi2022_sirius_formula_candidates.csv'
    status_rows = []
    all_rows = []
    commands = []
    for _, row in spec_df.iterrows():
        spec_id = safe_text(row.get('spec_id'))
        one_df = pd.DataFrame([row])
        one_mgf = single_dir / f'casmi_spec_{spec_id}.mgf'
        one_project = project_root / f'casmi_spec_{spec_id}'
        write_mgf(one_df, one_mgf)
        if one_project.exists() and args.force:
            shutil.rmtree(one_project)
        cmd = [
            str(sirius_bin), '-i', str(one_mgf), '-o', str(one_project), '--recompute', '--cores', str(args.cores),
            'formula', '-c', str(args.candidates), '-E', 'CHNOPSClBrIF', '--compound-timeout', str(args.compound_timeout)
        ]
        commands.append(' '.join(shlex_quote(x) for x in cmd))
        log_path = logdir / f'sirius_casmi_spec_{spec_id}.log'
        if args.force or not any(one_project.glob('*/formula_candidates.tsv')):
            try:
                with log_path.open('w', encoding='utf-8') as log:
                    completed = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, check=False, timeout=args.compound_timeout + 120)
                returncode = completed.returncode
                error = '' if returncode == 0 else f'SIRIUS return code {returncode}'
            except subprocess.TimeoutExpired:
                returncode = 124
                error = f'SIRIUS subprocess timeout after {args.compound_timeout + 120}s'
        else:
            returncode = 0
            error = ''
        parsed = normalize_scores(parse_candidates(one_project))
        if parsed.empty:
            status = 'no_formula_candidates' if returncode == 0 else 'sirius_failed'
            all_rows.append({
                'spectrum_id': spec_id,
                'candidate_formula': '',
                'sirius_native_formula_score_raw': math.nan,
                'sirius_native_formula_rank': math.nan,
                'sirius_native_status': status,
                'error_message': error,
                'sirius_source_file': '',
                'sirius_native_formula_score': math.nan,
                'sirius_command': ' '.join(shlex_quote(x) for x in cmd),
            })
        else:
            parsed['sirius_command'] = ' '.join(shlex_quote(x) for x in cmd)
            all_rows.extend(parsed.to_dict(orient='records'))
            status = 'available' if parsed['sirius_native_status'].eq('available').any() else 'no_formula_candidates'
        status_rows.append({'spectrum_id': spec_id, 'returncode': returncode, 'status': status, 'error_message': error, 'log_path': str(log_path), 'project': str(one_project)})

    Path(outdir / 'sirius_commands_used.sh').write_text('#!/usr/bin/env bash\n' + '\n'.join(commands) + '\n', encoding='utf-8')
    parsed_all = pd.DataFrame(all_rows)
    parsed_all.to_csv(formula_csv, index=False)
    status_df = pd.DataFrame(status_rows)
    status_df.to_csv(outdir / 'casmi2022_sirius_run_status.csv', index=False)
    audit = {
        'total_casmi_spectra': int(len(spec_df)),
        'parsed_formula_rows': int(len(parsed_all)),
        'spectra_with_formula_candidates': int(parsed_all.loc[parsed_all['sirius_native_status'].eq('available'), 'spectrum_id'].nunique()) if not parsed_all.empty else 0,
        'failed_spectra': int(status_df['status'].ne('available').sum()) if not status_df.empty else 0,
        'output_csv': str(formula_csv),
        'sirius_bin': str(sirius_bin),
        'mode': 'per-spectrum native SIRIUS 4.9.15 formula execution; no fallback scores',
        'sirius_version_stdout': subprocess.run([str(sirius_bin), '--version'], capture_output=True, text=True, check=False, timeout=60).stdout,
    }
    (outdir / 'casmi2022_sirius_formula_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    pd.DataFrame([audit]).to_csv(outdir / 'casmi2022_sirius_formula_audit.csv', index=False)
    print(json.dumps(audit, indent=2))


def shlex_quote(value: str) -> str:
    import shlex
    return shlex.quote(str(value))


if __name__ == '__main__':
    main()
