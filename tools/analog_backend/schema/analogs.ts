// Contract for output/analogs_results.json  (schemaVersion "1.0"). Non-finite numbers are serialised as null.
export type DatasetSource = 'NLDAS' | 'RCM_Arctic' | 'RCM_Antarctic';

export interface AnalogSite {
  id: string;
  name: string;
  coordinates: [lat: number, lon: number];
  datasetSource: DatasetSource;
  targetBody: 'Moon' | 'Mars';
  regimeCluster: number | null; // cluster ids are namespaced per source: NLDAS 0.., RCM_Arctic 100.., RCM_Antarctic 200..
  comparison: {
    similarityIndex: number | null;      // MCSI 0..1
    noveltyScore: number | null;         // 0..1, distance from classical analog sites (saturates at 1500 km)
    geometryMatch: number | null;        // 0..1, slope/roughness/shadow vs lunar target (absolute units)
    thermalQuantileMatch: number | null; // 0..1, within-planet thermal quantiles; null for SAR-only RCM cells
  };
  dataGaps: {
    temporalGapRatio: number | null;     // fraction of missing hourly samples; null without a time series
    spatialUncertainty: number | null;   // composite gap index 0..1 (rank-normalised)
    isCriticalZone: boolean;             // extreme microclimate AND poorly observed
  };
  variables: {
    tempQuantile: number | null;         // within-Earth quantile of the cold-tail skin temperature (0..1)
    radiation: number | null;            // mean net shortwave, W m-2
    soilMoisture: number | null;         // Noah 0-10 cm, kg m-2
    windSpeed: number | null;            // m s-1
    slope: number | null;                // degrees, at the shared geometry baseline
    roughness: number | null;            // metres RMS height, at the shared geometry baseline
  };
}

export interface AnalogsResults {
  meta: {
    schemaVersion: string; generatedAt: string; targetBody: string; nSites: number; nCellsScored: number;
    [k: string]: unknown;
  };
  sites: AnalogSite[];
}
