#!/usr/bin/env python3
"""Export PFAS selected-case peak-level annotations from existing SIRIUS projects."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path('/home/zhome/ec_tp_work/ec-transformation-product-model-v1/outputs/pfas_sirius_formula_scores_v1/sirius_project')
CASE_FILE = ROOT / 'results' / 'case_studies' / 'pfas_selected_cases.csv'
OUT = ROOT / 'results' / 'case_studies' / 'pfas_case_peak_annotations.csv'
STATUS = ROOT / 'results' / 'case_studies' / 'peak_annotation_status.json'
FIGDIR = ROOT / 'results' / 'figures' / 'pfas_case_spectra'

DIAGNOSTIC_MZ = {
    69.0: 'PFAS diagnostic m/z 69 (CF3-related)',
    80.0: 'PFAS sulfonate diagnostic m/z 80 (SO3-related)',
    99.0: 'PFAS diagnostic m/z 99 (FSO3/C2F3-related)',
    119.0: 'PFAS diagnostic m/z 119 (C2F5-related)',
    169.0: 'PFAS diagnostic m/z 169 (C3F7-related)',
    219.0: 'PFAS diagnostic m/z 219 (perfluoroalkyl-chain related)',
}


def find_case_dir(project: Path, query_id: str) -> Path | None:
    hits = sorted(project.glob(f'*{query_id}*'))
    return hits[0] if hits else None


def parse_spectrum_ms(path: Path) -> tuple[float | None, list[tuple[float, float]]]:
    parent = None
    peaks = []
    in_ms2 = False
    for line in path.read_text(errors='ignore').splitlines():
        s = line.strip()
        if not s:
            continue
        if s.lower().startswith('>parentmass'):
            try:
                parent = float(s.split(maxsplit=1)[1])
            except Exception:
                pass
        elif s.lower().startswith('>ms2'):
            in_ms2 = True
        elif s.startswith('>'):
            in_ms2 = False
        elif in_ms2:
            parts = s.split()
            if len(parts) >= 2:
                try:
                    peaks.append((float(parts[0]), float(parts[1])))
                except Exception:
                    pass
    return parent, peaks


def nearest_diagnostic(mz: float, tolerance: float = 0.35) -> str:
    for dmz, label in DIAGNOSTIC_MZ.items():
        if abs(mz - dmz) <= tolerance:
            return label
    return ''


def load_assignments(case_dir: Path) -> dict[float, dict[str, Any]]:
    out = {}
    for tsv in (case_dir / 'spectra').glob('*.tsv'):
        try:
            df = pd.read_csv(tsv, sep='\t')
        except Exception:
            continue
        for _, row in df.iterrows():
            try:
                mz = float(row.get('mz'))
            except Exception:
                continue
            out[mz] = {
                'assigned_fragment_formula': row.get('formula', ''),
                'annotation_source': str(tsv),
            }
    return out


def assignment_for(mz: float, assignments: dict[float, dict[str, Any]], tolerance: float = 0.02) -> dict[str, Any]:
    if not assignments:
        return {}
    nearest = min(assignments, key=lambda x: abs(x - mz))
    if abs(nearest - mz) <= tolerance:
        return assignments[nearest]
    return {}


def main() -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cases = pd.read_csv(CASE_FILE)
    searched = []
    rows = []
    generated_plots = []
    for _, case in cases.iterrows():
        query_id = str(case.get('query_id'))
        case_id = str(case.get('case_id'))
        case_dir = find_case_dir(DEFAULT_PROJECT, query_id)
        searched.append({'query_id': query_id, 'searched_project': str(DEFAULT_PROJECT), 'matched_dir': str(case_dir) if case_dir else ''})
        if case_dir is None:
            continue
        spectrum = case_dir / 'spectrum.ms'
        if not spectrum.exists():
            continue
        parent_mz, peaks = parse_spectrum_ms(spectrum)
        if not peaks:
            continue
        max_i = max(i for _, i in peaks) or 1.0
        assignments = load_assignments(case_dir)
        for mz, intensity in peaks:
            rel = 100.0 * intensity / max_i
            ann = assignment_for(mz, assignments)
            label = nearest_diagnostic(mz)
            neutral_loss = '' if parent_mz is None else f'{parent_mz - mz:.4f}'
            confidence = 'sirius_fragment_formula' if ann.get('assigned_fragment_formula') else ('diagnostic_mz_rule' if label else 'observed_peak')
            rows.append({
                'case_id': case_id,
                'query_id': query_id,
                'compound_name': case.get('compound_name', ''),
                'mz': mz,
                'intensity': intensity,
                'relative_intensity': rel,
                'assigned_fragment_formula': ann.get('assigned_fragment_formula', ''),
                'neutral_loss': neutral_loss,
                'diagnostic_fragment_label': label,
                'annotation_source': ann.get('annotation_source', str(spectrum)),
                'confidence': confidence,
                'notes': 'Observed experimental peak from SIRIUS-imported spectrum.ms; formulas from SIRIUS spectra TSV when available.',
            })
        xs = [mz for mz, _ in peaks]
        ys = [100.0 * i / max_i for _, i in peaks]
        colors = ['#d62728' if nearest_diagnostic(mz) else '#2f5d8c' for mz in xs]
        plt.figure(figsize=(8, 4.5))
        plt.vlines(xs, 0, ys, colors=colors, linewidth=1.8)
        for mz, rel in zip(xs, ys):
            label = nearest_diagnostic(mz)
            if label:
                plt.text(mz, rel + 3, f'{mz:.0f}', rotation=90, ha='center', va='bottom', fontsize=8)
        plt.xlabel('m/z')
        plt.ylabel('Relative intensity')
        plt.title(f'{case_id}: {query_id}')
        plt.ylim(0, max(110, max(ys) + 15))
        plt.tight_layout()
        plot_path = FIGDIR / f'{case_id}_{query_id}_spectrum.png'
        plt.savefig(plot_path, dpi=300)
        plt.close()
        generated_plots.append(str(plot_path))
    if rows:
        pd.DataFrame(rows).to_csv(OUT, index=False)
    status = {
        'peak_level_annotations_available': bool(rows),
        'rows_written': len(rows),
        'output_csv': str(OUT) if rows else '',
        'searched_files': searched,
        'generated_plots': generated_plots,
        'blocker': '' if rows else 'No matching SIRIUS spectrum.ms files with MS2 peaks were found for selected cases.',
    }
    STATUS.write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
