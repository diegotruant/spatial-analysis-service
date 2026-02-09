# Garmin FIT SDK Installation

To generate real binary `.fit` files, this service requires the official **FitCSVTool.jar** from the Garmin FIT SDK.

## Installation Steps
1. Download the FIT SDK (freely available) from: [https://developer.garmin.com/fit/download/](https://developer.garmin.com/fit/download/)
2. Unzip the downloaded file.
3. Locate `FitCSVTool.jar` inside the `java` folder.
4. Copy `FitCSVTool.jar` into this directory:
   `spatial-analysis-service/libs/`

## Current Status
If `FitCSVTool.jar` is missing, the service will run in **Mock Mode**, generating text files with a `.fit` extension to verify the API flow without crashing.
