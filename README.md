# Wattwise: Smart Energy Audit Demo

A small local Python dashboard based on the attached Experiment 1 report. It demonstrates live-style load monitoring, an illustrative NILM-style breakdown, demand and power-quality alerts, and energy/cost/carbon estimates for residential, commercial, and industrial profiles.

## Run it

1. Install Python 3.9 or newer if needed.
2. Open Terminal in this folder.
3. Run `python3 app.py` (Windows: `py app.py`).
4. Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser.
5. Stop the server with `Ctrl+C`.

The app uses only Python's standard library and requires no network connection or package installation.

## Publish a public website

The repository includes `render.yaml` for deployment to Render. Create a GitHub repository and upload the project files, then connect that repository in Render using **New → Blueprint** and apply the `render.yaml` configuration. Render will build and provide a public `onrender.com` URL. The GitHub repository can remain private. Render free web services may sleep after inactivity and take time to wake when a visitor returns.

Do not upload credentials, `.env` files, or private data. This demo currently uses simulated readings and has no login or access control; anyone with the public URL can open it. See [Render's deployment guide](https://render.com/docs/your-first-deploy) for current provider setup details.

## Try different monitoring scenarios

- Switch **Facility profile** between Residential, Commercial, and Industrial.
- Select or clear individual load chips to change which loads are monitored.
- Adjust supply voltage, power factor, energy tariff, and demand alert threshold. The dashboard updates as you move each control.
- Watch the load curve, per-load contribution, electrical parameter estimates, and alerts respond.
- Export the active configuration and audit estimates with **Export audit JSON**.

## How the demo estimates readings

Loads are synthetic profile values with a time-of-day pattern and small fluctuations. Active power is summed from the selected loads. Current, apparent power, and reactive power are derived from voltage and power factor. Energy, cost, and carbon figures use a representative daily utilization assumption, the tariff you set, and a demonstration grid factor of 0.42 kg CO2/kWh.

This is a learning prototype, not a sensor-connected meter or certified audit. The NILM-style breakdown is profile-based, not a trained appliance classifier. For actual measurements, connect calibrated CT and voltage sensors through a suitable gateway and replace the profile generator with the device data feed. The report's suggested ESP32/CT sensor/MQTT architecture is a conceptual integration path.

## Example dataset

`sample_energy_readings.csv` contains 456 synthetic hourly load readings across Residential, Commercial, and Industrial sites for September 30, 2026. Each row represents one load during one hour. `energy_kwh` is set to the hourly average `active_power_kw` (a one-hour interval); current is calculated from active power, voltage, and power factor. The data is for experimenting with spreadsheet analysis or for adapting a future CSV import. The current dashboard does not import CSV files; it generates its own simulated values.
