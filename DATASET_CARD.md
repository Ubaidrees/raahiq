# RaahIQ — Karachi Public Transit Routes Dataset

## Overview

This dataset provides a structured, geocoded, and community-verified collection of
Karachi's public transit routes — Mini Buses, Coaches, Other Buses, Red Buses, EV
Buses, and BRT (Bus Rapid Transit) lines. It powers [RaahIQ](https://raahiq.streamlit.app),
a free commute-planning app for Karachi commuters, and is published separately so
researchers, students, and developers working on transit accessibility, urban
mobility, or NLP/geocoding problems in Pakistan can use it too.

- **70+ routes** across 6 categories (Mini Bus, Coach, Other Bus, Red Bus, EV Bus, BRT)
- **677 unique stops**, each geocoded to real-world coordinates (latitude/longitude)
- Actively maintained: corrections are made based on real commuter feedback

## Files

| File | Description |
|---|---|
| `bus_routes.json` | Route-level data: route ID, category, and an ordered list of stop names |
| `stop_coordinates.json` | Stop-level data: `{stop_name: [longitude, latitude]}` for all 677 unique stops |

### `bus_routes.json` schema
```json
{
  "routes": [
    {
      "id": "W-11",
      "category": "Mini Bus",
      "stops": ["Ahsanabad", "New Karachi Allah Wali Chorangi", "...", "Keamari"]
    }
  ]
}
```

### `stop_coordinates.json` schema
```json
{
  "Tower": [67.0011, 24.8607],
  "Saddar": [67.0299, 24.8557]
}
```
Coordinates are `[longitude, latitude]`, geocoded via OpenRouteService and
constrained to Karachi's geographic bounding box for accuracy.

## How this dataset was compiled

The base route and stop list was originally compiled from a publicly shared
Karachi transit route guide (images summarizing Mini Bus, Coach, Red Bus, EV
Bus, and BRT routes) circulating on Facebook. Starting from that base:

1. **Transcription & structuring** — the route/stop information was manually
   transcribed from image form into structured JSON.
2. **Data cleaning** — transcription artifacts (e.g. malformed stop entries
   from comma-separated route numbers) were identified and corrected.
3. **Geocoding** — every unique stop name (677 total) was geocoded to real
   GPS coordinates via the OpenRouteService API, with a Karachi-bounded
   search to avoid mismatches with same-named places elsewhere.
4. **Matching-safe normalization** — a word-level fuzzy-matching layer was
   built to reliably match user-typed locations (which rarely match stop
   names exactly) to the correct stop, while avoiding false matches between
   textually similar but genuinely different Karachi places (e.g. "Korangi"
   vs "Orangi" vs "Chorangi"; "Malir Halt" vs "Malir Cantt").
5. **Ongoing community verification** — since RaahIQ went live, real
   commuters have reported routing errors and gaps via an in-app feedback
   channel, and the dataset is corrected accordingly on an ongoing basis.

## Known limitations

- The original route guide lists **major stops only** — real buses stop at
  many more points along each route than are listed here. Two genuinely
  close stops may appear under different names (e.g. "Star Gate" vs "Colony
  Gate") since the source guide wasn't stop-by-stop exhaustive.
- Fare information is intentionally **not included** — no reliable, current
  source for real-time Karachi bus fares was available at compilation time.
- Route data reflects conditions as of the "last updated" date below; public
  transit routes can change over time.

**Last verified:** update this date whenever you do a verification pass.

## License

Licensed under **CC BY 4.0** (Creative Commons Attribution 4.0 International).
You may use, share, and adapt this dataset for any purpose, including
commercially, as long as you give appropriate credit.

## Citation

If you use this dataset, please cite it as:

> Idrees, M. U. (2026). *RaahIQ: Karachi Public Transit Routes Dataset* [Data set].
> Zenodo. https://doi.org/XX.XXXX/zenodo.XXXXXXX

(Replace the DOI above once assigned by Zenodo — see publishing steps.)

## About RaahIQ

RaahIQ is a free, community-driven commute planner for Karachi, built by
Muhammad Ubaid Idrees, a BS Artificial Intelligence student at Dawood
University of Engineering & Technology (DUET), Karachi. It started as a
response to a recurring question in a local Facebook transport group:
"which bus goes from here?" — Live app: https://raahiq.streamlit.app