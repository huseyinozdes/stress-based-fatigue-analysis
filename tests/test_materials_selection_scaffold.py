"""
Tests for the materials-selection scaffold.

These tests verify structure, type correctness, and basic logic of the
scaffold modules only; they do NOT validate engineering accuracy (that
requires literature-calibrated data not yet available).
"""
from __future__ import annotations

import pytest

from materials_selection_stubs import STUB_MATERIALS, AISI_4340, AL_6061_T6
from materials_selection_types import (
    SelectionConstraint,
    SelectionCriteria,
)
from materials_selection_service import (
    evaluate_candidates,
    build_ashby_payload,
)


# ---------------------------------------------------------------------------
# evaluate_candidates
# ---------------------------------------------------------------------------

class TestEvaluateCandidates:
    def test_returns_all_candidates(self):
        result = evaluate_candidates(STUB_MATERIALS)
        assert len(result.candidates) == len(STUB_MATERIALS)

    def test_no_constraints_all_feasible(self):
        result = evaluate_candidates(STUB_MATERIALS)
        assert all(c.feasible for c in result.candidates)

    def test_constraint_filters_low_strength(self):
        # Only high-strength steels / titanium should pass Sy >= 500 MPa
        constraint = SelectionConstraint("yield_strength_mpa", min_value=500.0)
        result = evaluate_candidates(STUB_MATERIALS, constraints=[constraint])
        feasible_names = [c.properties.name for c in result.candidates if c.feasible]
        assert AISI_4340.name in feasible_names
        # Low-carbon steel (210 MPa) must be excluded
        assert not any("1020" in n for n in feasible_names)

    def test_ranked_list_subset_of_feasible(self):
        constraint = SelectionConstraint("density_kg_m3", max_value=5_000.0)
        result = evaluate_candidates(STUB_MATERIALS, constraints=[constraint])
        feasible_names = {c.properties.name for c in result.candidates if c.feasible}
        ranked_names = {c.properties.name for c in result.ranked}
        assert ranked_names <= feasible_names

    def test_ranking_honours_criteria_direction(self):
        # Maximise ultimate_strength_mpa → AISI 4340 (1280 MPa) should rank first
        criteria = [SelectionCriteria("ultimate_strength_mpa", weight=1.0, maximize=True)]
        result = evaluate_candidates(STUB_MATERIALS, criteria=criteria)
        if result.ranked:
            assert result.ranked[0].properties.name == AISI_4340.name

    def test_feasibility_constraint_violations_recorded(self):
        constraint = SelectionConstraint("yield_strength_mpa", min_value=2_000.0)
        result = evaluate_candidates(STUB_MATERIALS, constraints=[constraint])
        for cand in result.candidates:
            assert not cand.feasible
            assert len(cand.constraint_violations) > 0

    def test_result_notes_present(self):
        result = evaluate_candidates(STUB_MATERIALS)
        assert isinstance(result.notes, list) and len(result.notes) > 0


# ---------------------------------------------------------------------------
# Fatigue metrics derivation
# ---------------------------------------------------------------------------

class TestFatigueMetrics:
    def test_fatigue_metrics_populated(self):
        result = evaluate_candidates([AISI_4340])
        cand = result.candidates[0]
        assert cand.fatigue_metrics is not None
        assert cand.fatigue_metrics.endurance_ratio > 0.0
        assert cand.fatigue_metrics.specific_endurance > 0.0

    def test_endurance_ratio_range(self):
        # Endurance ratio Se/Sut should be in (0, 1)
        result = evaluate_candidates(STUB_MATERIALS)
        for cand in result.candidates:
            er = cand.fatigue_metrics.endurance_ratio
            assert 0.0 < er < 1.0, f"Unexpected endurance ratio {er} for {cand.properties.name}"

    def test_aluminium_endurance_estimated_when_provided(self):
        # AL_6061_T6 has endurance_limit_mpa set → should be used directly
        result = evaluate_candidates([AL_6061_T6])
        cand = result.candidates[0]
        expected_ratio = AL_6061_T6.endurance_limit_mpa / AL_6061_T6.ultimate_strength_mpa
        assert abs(cand.fatigue_metrics.endurance_ratio - expected_ratio) < 1e-6


# ---------------------------------------------------------------------------
# build_ashby_payload
# ---------------------------------------------------------------------------

class TestBuildAshbyPayload:
    def test_payload_has_correct_property_names(self):
        payload = build_ashby_payload(
            STUB_MATERIALS,
            x_property="youngs_modulus_mpa",
            y_property="density_kg_m3",
        )
        assert payload.x_property == "youngs_modulus_mpa"
        assert payload.y_property == "density_kg_m3"

    def test_all_complete_materials_included(self):
        payload = build_ashby_payload(
            STUB_MATERIALS,
            x_property="youngs_modulus_mpa",
            y_property="density_kg_m3",
        )
        # All STUB_MATERIALS have both properties → all should appear
        assert len(payload.points) == len(STUB_MATERIALS)

    def test_selected_flag_propagated(self):
        payload = build_ashby_payload(
            STUB_MATERIALS,
            x_property="youngs_modulus_mpa",
            y_property="density_kg_m3",
            selected_names=[AISI_4340.name],
        )
        selected = [p for p in payload.points if p.selected]
        assert len(selected) == 1
        assert selected[0].name == AISI_4340.name

    def test_missing_property_skipped(self):
        # Use a property that is None for Nylon (fracture_toughness_mpa_sqrtm)
        payload = build_ashby_payload(
            STUB_MATERIALS,
            x_property="youngs_modulus_mpa",
            y_property="fracture_toughness_mpa_sqrtm",
        )
        names = [p.name for p in payload.points]
        # Nylon has no fracture_toughness_mpa_sqrtm → should be skipped
        assert not any("Nylon" in n for n in names)

    def test_computed_metric_axis(self):
        # specific_endurance comes from FatigueMetrics, not MaterialProperties
        payload = build_ashby_payload(
            STUB_MATERIALS,
            x_property="density_kg_m3",
            y_property="specific_endurance",
        )
        assert len(payload.points) == len(STUB_MATERIALS)
        for pt in payload.points:
            assert pt.y > 0.0
