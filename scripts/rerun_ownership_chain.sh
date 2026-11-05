#!/bin/bash
# Rebuild the ownership-dependent panels and rerun the results, in dependency order.
# Stops at the first failure. Logs per step in .superpowers/logs/rerun/.
cd /Users/theodor/projects/vre_spain_thesis || exit 1
L=.superpowers/logs/rerun; mkdir -p $L
P=.venv/bin/python
step() { name=$1; shift; echo "$(date '+%H:%M:%S') START $name"; "$@" > "$L/$name.log" 2>&1; rc=$?;
         echo "$(date '+%H:%M:%S') END   $name exit $rc"; [ $rc -eq 0 ] || { echo "CHAIN STOPPED at $name"; exit $rc; }; }
[ -n "$FROM" ] || step 01_contract_position   $P scripts/build/build_contract_position.py --save --tier owner
[ -n "$FROM" ] || step 02_residual_demand     $P scripts/analysis/residual_demand_firm.py --tier owner --full --save
[ -n "$FROM" ] || step 03_firm_incentive      $P scripts/analysis/firm_incentive_rebuild.py
step 04_firm_x              $P scripts/analysis/firm_x.py
step 05_rival_solar         $P scripts/build/build_rival_solar.py
step 06_rival_wind          $P scripts/build/build_rival_solar.py --tech wind
step 07_solar_instrument    $P scripts/build/build_solar_instrument.py
step 08_check_rival_solar   $P scripts/qa/check_rival_solar.py
step 09_check_rival_wind    $P scripts/qa/check_rival_solar.py --tech wind
step 10_leg_c_panel         $P scripts/analysis/leg_c_panel.py
step 11_check_leg_c_panel   $P scripts/qa/check_leg_c_panel.py
step 12_leg_d_panel         $P scripts/analysis/leg_d_panel.py
step 13_check_leg_d_panel   $P scripts/qa/check_leg_d_panel.py
step 14_check_exposed       $P scripts/qa/check_exposed_position.py
step 15_leg_c_test          $P scripts/analysis/leg_c_test.py
step 16_leg_d_sign_test     $P scripts/analysis/leg_d_sign_test.py
step 17_leg_d_forecast      $P scripts/analysis/leg_d_forecast_test.py
step 18_forecast_first      $P scripts/analysis/forecast_first_stage.py
step 19_rain_first          $P scripts/analysis/hydro_rain_first_stage.py
echo "CHAIN DONE"
