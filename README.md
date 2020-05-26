# API status page script
Takes an `api_status.json` log file from the [Integration Test Lite](https://github.com/osu-mist/integration-test-lite)
job, then creates and/or updates incidents on the status page via Cachet's API.

## Instructions
1. Copy and rename `configuration_example.json` as `configuration.json`.
2. Build the Docker image
    ```
    $ docker build -t api-status-page-script .
    ```
3. Run the Docker image
    ```
    $ docker run api-status-page-script
    ```

## Components and Incidents
The status page is based around the Component and Incident resources. The components represent the APIs being
monitored and have their own status values ranging from 'Operational' to 'Major Outage'. As test failures are reported
by the [Integration Test Lite](https://github.com/osu-mist/integration-test-lite) job, incidents will be created for the
broken components. These incidents have their own status values, **independent of their component's status**. When
making API calls, component and incident status values are represented as integers.

### Component Status Codes:
```
0 - Unknown
1 - Operational
2 - Performance Issues
3 - Partial Outage
4 - Major Outage
```

### Incident Status Codes
```
1 - Investigating
2 - Identified
3 - Watching
4 - Fixed
```
