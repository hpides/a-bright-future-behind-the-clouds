from helpers import HOURS_PER_YEAR, npv_of_cash_flows, discount_factor


class Alternative:
    """
    An investment alternative (local or cloud) with the data needed to
    compute its present worth of costs.
    """

    def __init__(self, name, type, lifetime, capex=0.0,
                 annual_opex=None, opex_growth=0.0,
                 tdp_watts=None, utilization=None, energy_price=None,
                 idle_watts=None,
                 baseline_utilization=None, database_utilization=None,
                 hourly_rate=None, hours_per_year=None, discount_on_rate=0.0,
                 salvage=0.0):
        self.name = name
        self.type = type
        self.lifetime = lifetime
        self.capex = float(capex)

        # OPEX
        self.annual_opex = float(annual_opex) if annual_opex is not None else None
        self.opex_growth = float(opex_growth)

        # Power / energy (local)
        self.tdp_watts = tdp_watts
        self.utilization = utilization                  # 0–1 (cloud)
        self.baseline_utilization = baseline_utilization  # 0–1 (local, without db)
        self.database_utilization = database_utilization  # 0–1 (local db increment, optional)
        self.energy_price = energy_price    # €/kWh
        # Idle power draw; defaults to half of TDP if not given.
        if idle_watts is None and tdp_watts is not None:
            idle_watts = 0.5 * tdp_watts
        self.idle_watts = idle_watts

        # Cloud-specific
        self.hourly_rate = hourly_rate
        self.hours_per_year = hours_per_year
        self.discount_on_rate = discount_on_rate

        self.salvage = float(salvage)

    @classmethod
    def local(cls, name, capex, lifetime,
              tdp_watts=None, baseline_utilization=None, energy_price=None,
              idle_watts=None, database_utilization=None,
              base_annual_opex=0.0, opex_growth=0.0, salvage=0.0):
        """
        tdp_watts: chip/system TDP in watts (e.g. 80), the power draw at 100%
            utilization.
        baseline_utilization: fraction [0,1] representing system utilization
            without the database workload.
        database_utilization: optional fraction [0,1] for additional utilization
            due to the database workload. If provided, OPEX is the incremental
            cost: opex(baseline + database) - opex(baseline).
        idle_watts: power draw at 0% utilization; defaults to half of TDP.
            Actual power scales linearly from idle_watts (at u=0) to tdp_watts
            (at u=1).
        energy_price: €/kWh
        If tdp_watts, baseline_utilization, and energy_price are all given,
        energy OPEX will be derived from them; otherwise base_annual_opex is used.
        """
        return cls(
            name=name,
            type="local",
            lifetime=lifetime,
            capex=capex,
            annual_opex=base_annual_opex,
            opex_growth=opex_growth,
            tdp_watts=tdp_watts,
            baseline_utilization=baseline_utilization,
            database_utilization=database_utilization,
            energy_price=energy_price,
            idle_watts=idle_watts,
            salvage=salvage,
        )

    @classmethod
    def cloud(cls, name, lifetime,
              annual_opex=None, hourly_rate=None, hours_per_year=None,
              utilization=None, discount_on_rate=0.0, opex_growth=0.0):
        """
        utilization: fraction [0,1] applied to hours_per_year for
        rate-based costs (e.g. 0.5 uses 0.5 * hours_per_year).
        """
        return cls(
            name=name,
            type="cloud",
            lifetime=lifetime,
            capex=0.0,
            annual_opex=annual_opex,
            opex_growth=opex_growth,
            hourly_rate=hourly_rate,
            hours_per_year=hours_per_year,
            utilization=utilization,
            discount_on_rate=discount_on_rate,
        )

    def yearly_opex(self, year):
        """
        Returns OPEX in year `year` (1-based) with growth.
        """
        # Prefer TDP-based energy for local if all params are present
        if self.type == "local" and \
           self.tdp_watts is not None and \
           self.baseline_utilization is not None and \
           self.energy_price is not None:
            # Power scales linearly from idle (u=0) to TDP (u=1).
            idle = self.idle_watts if self.idle_watts is not None else 0.0
            if self.database_utilization is not None:
                # Incremental cost: opex(baseline + db) - opex(baseline)
                avg_watts_total = idle + (self.tdp_watts - idle) * (self.baseline_utilization + self.database_utilization)
                avg_watts_base = idle + (self.tdp_watts - idle) * self.baseline_utilization
                avg_watts = avg_watts_total - avg_watts_base
            else:
                avg_watts = idle + (self.tdp_watts - idle) * self.baseline_utilization
            avg_power_kw = avg_watts / 1000.0
            kwh_per_year = avg_power_kw * HOURS_PER_YEAR
            base = kwh_per_year * self.energy_price
        elif self.annual_opex is not None:
            base = self.annual_opex
        elif self.hourly_rate is not None and self.hours_per_year is not None:
            eff_rate = self.hourly_rate * (1.0 - self.discount_on_rate)
            eff_hours = self.hours_per_year
            if self.utilization is not None:
                eff_hours *= self.utilization
            base = eff_rate * eff_hours
        else:
            base = 0.0

        return base * ((1.0 + self.opex_growth) ** year)

    def cash_flows(self):
        """
        Returns a dict {year: cash_flow} with year 0..lifetime.
        Negative = cost (CAPEX/OPEX), positive = salvage, etc.
        """
        n = self.lifetime
        cf = {}

        # Year 0: CAPEX
        cf[0] = -self.capex

        # OPEX years 0..n (year 0 combines with CAPEX)
        for t in range(0, n + 1):
            cf[t] = cf.get(t, 0.0) - self.yearly_opex(t)

        # Salvage at end
        if self.salvage != 0.0:
            cf[n] = cf.get(n, 0.0) + self.salvage

        return cf

    def present_worth_cost(self, r):
        """
        Present worth of all costs (CAPEX + OPEX - salvage).
        """
        return npv_of_cash_flows(self.cash_flows(), r)

    def cumulative_present_worth(self, r):
        """
        Returns (years, cumulative) where cumulative[i] is the present worth
        of all discounted cash flows from year 0 up to and including years[i].
        """
        cf = self.cash_flows()
        years = sorted(cf)
        cumulative = []
        running = 0.0
        for t in years:
            running += cf[t] * discount_factor(r, t)
            cumulative.append(running)
        return years, cumulative

    def cumulative_present_worth_daily(self, r):
        """
        Returns (days, cumulative) where days are in [0, 1, 2, ...] and
        cumulative[i] is the present worth of all discounted cash flows
        distributed daily. Capex is paid entirely at day 0, while OPEX is
        distributed uniformly across each year.
        """
        days_total = self.lifetime * 365
        days = list(range(days_total + 1))
        cumulative = []
        running = 0.0

        for day in days:
            # Calculate which year this day falls into
            year_frac = day / 365.0
            year = int(year_frac)
            
            pv_daily = 0.0
            
            # At day 0, pay the capex
            if day == 0:
                pv_daily += self.capex * discount_factor(r, 0.0)
            
            # Distribute annual OPEX uniformly across each year
            annual_opex = self.yearly_opex(year)
            daily_opex = annual_opex / 365.0
            pv_daily += daily_opex * discount_factor(r, year_frac)
            
            running += pv_daily
            cumulative.append(running)

        return days, cumulative
