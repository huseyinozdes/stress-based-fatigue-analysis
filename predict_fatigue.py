#!/usr/bin/env python3
"""
Command-line fatigue life predictor based on Özdeş thesis methodology.

Usage:
    python predict_fatigue.py --uts 300 --ys 200 --elongation 5 \
        --stress-amplitude 150 --mean-stress 50 --correction walker

    python predict_fatigue.py --csv-file tensile_data.csv --stress-amplitude 150
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from fatigue_engine import FatigueEngine, TensileProperties, FatigueCalculationError


def load_csv_tensile(csv_path: str) -> list[TensileProperties]:
    """Load tensile properties from CSV.
    
    Expected columns: uts, ys (optional), elongation_percent
    """
    tensile_list = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            uts = float(row['uts'])
            ys = float(row.get('ys', 0)) or None
            elongation = float(row['elongation_percent'])
            tensile_list.append(TensileProperties(uts=uts, ys=ys, elongation_percent=elongation))
    return tensile_list


def main():
    parser = argparse.ArgumentParser(
        description="Minimalist fatigue life predictor using Özdeş thesis methodology."
    )
    
    # Tensile property input
    parser.add_argument('--uts', type=float, help='Ultimate tensile strength (MPa)')
    parser.add_argument('--ys', type=float, help='Yield strength (MPa)')
    parser.add_argument('--elongation', type=float, help='Elongation at fracture (%%)')
    parser.add_argument('--csv-file', type=str, help='Load tensile data from CSV')
    
    # Fatigue loading
    parser.add_argument('--stress-amplitude', type=float, required=True, help='Alternating stress amplitude (MPa)')
    parser.add_argument('--mean-stress', type=float, default=0.0, help='Mean stress (MPa)')
    parser.add_argument('--stress-ratio', type=float, help='Stress ratio R (optional; inferred if not given)')
    
    # Model selection
    parser.add_argument('--correction', choices=['walker', 'soderberg', 'swt'], default='walker',
                       help='Mean stress correction model')
    parser.add_argument('--output', type=str, help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Load or create tensile properties
    if args.csv_file:
        tensile_list = load_csv_tensile(args.csv_file)
    else:
        if not all([args.uts, args.elongation]):
            parser.error("Provide either --csv-file or --uts and --elongation")
        tensile_list = [TensileProperties(uts=args.uts, ys=args.ys, elongation_percent=args.elongation)]
    
    engine = FatigueEngine()
    results = []
    success_count = 0
    error_count = 0
    
    for i, tensile in enumerate(tensile_list):
        try:
            result = engine.predict_from_tensile(
                tensile=tensile,
                stress_amplitude=args.stress_amplitude,
                mean_stress=args.mean_stress,
                stress_ratio_r=args.stress_ratio,
                correction=args.correction
            )
            result['sample_index'] = i
            results.append(result)
            
            # Print to console
            print(f"\n--- Sample {i} ---")
            print(f"Tensile: UTS={tensile.uts:.1f} MPa, YS={tensile.ys or 'N/A'} MPa, Elong={tensile.elongation_percent:.2f}%")
            print(f"Quality Index: {result['quality_index']:.3f}")
            print(f"Basquin: A={result['basquin_A']:.3e}, b={result['basquin_b']:.4f}")
            print(f"Correction: {result['correction_model']} (param={result['correction_parameter']:.3f})")
            print(f"Corrected Stress Amplitude: {result['corrected_stress_amplitude']:.2f} MPa")
            print(f"Predicted Cycles: {result['predicted_cycles']:.2e}")
            success_count += 1
            
        except FatigueCalculationError as e:
            print(f"Error in sample {i}: {e}", file=sys.stderr)
            results.append({'sample_index': i, 'error': str(e)})
            error_count += 1
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    print(f"\nRun summary: {len(results)} sample(s), {success_count} succeeded, {error_count} failed")


if __name__ == '__main__':
    main()
