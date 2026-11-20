import ast
from math import inf, nan, nextafter
from pathlib import Path
import unittest

from alternative import Alternative
from helpers import HOURS_PER_YEAR


class LocalSizingTests(unittest.TestCase):
    def local(self, cores=4, cloud_cores=8, cloud_utilization=0.30,
              baseline_utilization=0.1, capex=355, tdp_watts=25,
              idle_watts=None, energy_price=0.34, base_annual_opex=0.0,
              salvage=0.0, opex_growth=0.0, database_utilization=None):
        return Alternative.local(
            name="Pi5", capex=capex, lifetime=6, cores=cores,
            cloud_cores=cloud_cores, cloud_utilization=cloud_utilization,
            tdp_watts=tdp_watts, baseline_utilization=baseline_utilization,
            idle_watts=idle_watts, energy_price=energy_price,
            base_annual_opex=base_annual_opex, salvage=salvage,
            opex_growth=opex_growth, database_utilization=database_utilization,
        )

    def test_core_formula_for_all_machines(self):
        for cores, expected in [(4, 0.6), (10, 0.24), (16, 0.15),
                                (64, 0.0375), (192, 0.0125)]:
            with self.subTest(cores=cores):
                local = self.local(cores=cores)
                self.assertEqual(local.cores, cores)
                self.assertEqual(local.instance_count, 1)
                self.assertAlmostEqual(local.database_utilization, expected)

    def test_fleet_sizing_and_workload_conservation(self):
        for baseline in (0, 0.1, 0.3):
            for load, demand in [(0, 0), (0.3, 0.6), (0.6, 1.2),
                                 (0.9, 1.8), (1, 2)]:
                with self.subTest(baseline=baseline, load=load):
                    local = self.local(
                        baseline_utilization=baseline, cloud_utilization=load,
                    )
                    self.assertGreaterEqual(local.instance_count, 1)
                    self.assertLessEqual(
                        baseline + local.database_utilization, 1,
                    )
                    self.assertAlmostEqual(
                        local.instance_count * local.database_utilization, demand,
                    )
                    self.assertAlmostEqual(
                        local.instance_count * local.cores *
                        local.database_utilization, 8 * load,
                    )
                    self.assertEqual(local.capex, 355 * local.instance_count)
                    self.assertEqual(local.tdp_watts, 25 * local.instance_count)
                    self.assertEqual(local.idle_watts, 12.5 * local.instance_count)
                    self.assertAlmostEqual(
                        local.yearly_opex(0),
                        12.5 * demand / 1000 * HOURS_PER_YEAR * 0.34,
                    )

    def test_exact_capacity_and_overflow_boundaries(self):
        for baseline, boundary in [(0, 0.5), (0.1, 0.45), (0.3, 0.35)]:
            with self.subTest(baseline=baseline):
                at_capacity = self.local(
                    baseline_utilization=baseline, cloud_utilization=boundary,
                )
                over_capacity = self.local(
                    baseline_utilization=baseline,
                    cloud_utilization=nextafter(boundary, inf),
                )
                self.assertEqual(at_capacity.instance_count, 1)
                self.assertEqual(over_capacity.instance_count, 2)
        self.assertEqual(self.local(cloud_utilization=0.9).instance_count, 2)
        self.assertEqual(
            self.local(cloud_utilization=nextafter(0.9, inf)).instance_count, 3,
        )

    def test_120_percent_demand_is_split_evenly(self):
        local = self.local(cloud_utilization=0.6, idle_watts=5)
        self.assertEqual(local.instance_count, 2)
        self.assertEqual(local.capex, 710)
        self.assertEqual(local.tdp_watts, 50)
        self.assertEqual(local.idle_watts, 10)
        self.assertAlmostEqual(local.database_utilization, 0.6)
        self.assertAlmostEqual(local.yearly_opex(0), 71.4816)

    def test_no_capex_has_identical_power_and_load(self):
        paid = self.local(cloud_utilization=0.6)
        free = self.local(cloud_utilization=0.6, capex=0)
        self.assertEqual(free.capex, 0)
        for attribute in ("instance_count", "cores", "tdp_watts", "idle_watts",
                          "database_utilization"):
            self.assertEqual(getattr(free, attribute), getattr(paid, attribute))
        self.assertEqual(free.yearly_opex(0), paid.yearly_opex(0))

    def test_scaled_fleet_matches_equivalent_aggregate_cash_flows(self):
        fleet = self.local(cloud_utilization=0.6, idle_watts=5,
                           salvage=20, opex_growth=0.02)
        aggregate = Alternative.local(
            name="Aggregate", capex=710, lifetime=6, tdp_watts=50,
            idle_watts=10, baseline_utilization=0.1,
            database_utilization=0.6, energy_price=0.34,
            salvage=40, opex_growth=0.02,
        )
        self.assertEqual(fleet.cash_flows(), aggregate.cash_flows())
        self.assertEqual(fleet.present_worth_cost(0.05),
                         aggregate.present_worth_cost(0.05))
        self.assertEqual(fleet.cumulative_present_worth(0.05),
                         aggregate.cumulative_present_worth(0.05))
        self.assertEqual(fleet.cumulative_present_worth_daily(0.05),
                         aggregate.cumulative_present_worth_daily(0.05))

    def test_fallback_opex_and_salvage_scale(self):
        local = self.local(cloud_utilization=0.6, tdp_watts=None,
                           base_annual_opex=100, salvage=20, opex_growth=0.1)
        self.assertEqual(local.annual_opex, 200)
        self.assertEqual(local.salvage, 40)
        self.assertAlmostEqual(local.yearly_opex(1), 220)

    def test_optional_opex_and_numeric_cost_strings_remain_supported(self):
        local = self.local(cloud_utilization=0.6, tdp_watts=None,
                           base_annual_opex=None, capex="355", salvage="20")
        self.assertEqual(local.capex, 710)
        self.assertEqual(local.salvage, 40)
        self.assertIsNone(local.annual_opex)
        self.assertEqual(local.yearly_opex(0), 0)

    def test_invalid_workload_inputs_raise(self):
        cases = [
            {"cores": value}
            for value in (None, 0, -1, 4.5, True, inf, nan)
        ] + [
            {"cloud_cores": value}
            for value in (None, 0, -1, 8.5, True, inf, nan)
        ] + [
            {"cloud_utilization": value}
            for value in (None, -0.1, 1.1, inf, nan)
        ] + [
            {"baseline_utilization": value}
            for value in (None, -0.1, 1, 1.1, inf, nan)
        ] + [{"database_utilization": 0.6}]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.local(**overrides)

    def test_legacy_local_and_cloud_behavior(self):
        local = Alternative.local(
            "Legacy", 355, 6, 25, 0.1, 0.34, 5, 0.6,
        )
        self.assertEqual(local.instance_count, 1)
        self.assertIsNone(local.cores)
        self.assertAlmostEqual(local.yearly_opex(0), 35.7408)
        baseline_only = Alternative.local("Baseline", 355, 6, 25, 0.3, 0.34)
        self.assertAlmostEqual(
            baseline_only.yearly_opex(0), 16.25 / 1000 * HOURS_PER_YEAR * 0.34,
        )
        cloud = Alternative.cloud(
            "Cloud", 6, hourly_rate=0.45, hours_per_year=HOURS_PER_YEAR,
            utilization=1, cores=8,
        )
        self.assertEqual(cloud.cores, 8)
        self.assertEqual(cloud.yearly_opex(0), 3942)


class ExampleWiringTests(unittest.TestCase):
    def test_all_script_alternatives_use_global_workload(self):
        directory = Path(__file__).parent
        for filename, baseline in [
            ("make_all_examples.py", 0.1),
            ("make_m4_example.py", 0.3),
            ("make_pi5_r6a2xlarge_example.py", 0.3),
        ]:
            for load in (0.3, 0.6, 0.9, 1.0):
                with self.subTest(script=filename, load=load):
                    tree = ast.parse((directory / filename).read_text())
                    assignments = []
                    for node in tree.body:
                        if not isinstance(node, ast.Assign):
                            continue
                        is_workload = any(
                            isinstance(target, ast.Name) and target.id in
                            ("CLOUD_CORES", "CLOUD_UTILIZATION")
                            for target in node.targets
                        )
                        is_alternative = (
                            isinstance(node.value, ast.Call) and
                            isinstance(node.value.func, ast.Attribute) and
                            isinstance(node.value.func.value, ast.Name) and
                            node.value.func.value.id == "Alternative"
                        )
                        if is_workload or is_alternative:
                            assignments.append(node)
                    module = ast.Module(body=assignments, type_ignores=[])
                    namespace = {"Alternative": Alternative}
                    exec(compile(module, filename, "exec"), namespace)
                    self.assertEqual(namespace["CLOUD_UTILIZATION"], 0.3)
                    self.assertEqual(namespace["CLOUD_CORES"], 8)
                    for node in assignments:
                        if node.targets[0].id == "CLOUD_UTILIZATION":
                            node.value = ast.copy_location(ast.Constant(load), node.value)
                    exec(compile(module, filename, "exec"), namespace)
                    locals_found = 0
                    for alternative in namespace.values():
                        if not isinstance(alternative, Alternative):
                            continue
                        if alternative.type == "cloud":
                            self.assertEqual(alternative.utilization, 1)
                            continue
                        locals_found += 1
                        self.assertEqual(alternative.baseline_utilization, baseline)
                        self.assertAlmostEqual(
                            alternative.instance_count * alternative.cores *
                            alternative.database_utilization, 8 * load,
                        )
                        self.assertLessEqual(
                            baseline + alternative.database_utilization, 1,
                        )
                    self.assertEqual(locals_found, 10 if baseline == 0.1 else 2)


if __name__ == "__main__":
    unittest.main()
