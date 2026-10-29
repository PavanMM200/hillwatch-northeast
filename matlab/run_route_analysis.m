function run_route_analysis(manifestPath)
% Experimental threshold detector. Outputs candidates, never confirmed landslides.
cfg = jsondecode(fileread(manifestPath));
assert(isequal(string(cfg.sar_bands(:)),["VV";"VH"]),'hill:Bands','Expected VV,VH band order');
assert(cfg.nodata == -9999,'hill:NoData','Unsupported no-data convention');
assert(numel(cfg.scenes)>=2,'hill:Dates','Two real acquisition records required');
assert(~strcmp(cfg.scenes(1).acquired_at,cfg.scenes(2).acquired_at),'hill:Dates','Distinct acquisitions required');
[before,R] = readgeoraster(cfg.files.sar_before,'OutputType','double');
[after,R2] = readgeoraster(cfg.files.sar_after,'OutputType','double');
align_multitemporal_images(before,R,after,R2,cfg.files.sar_before,cfg.files.sar_after);
assert(size(before,3)==2 && size(after,3)==2,'hill:Bands','Two SAR bands required');
[a,va] = preprocess_sar(before,cfg.sar_units,cfg.nodata);
[b,vb] = preprocess_sar(after,cfg.sar_units,cfg.nodata);
[terrain,Rt] = readgeoraster(cfg.files.terrain,'OutputType','double');
align_multitemporal_images(before(:,:,1),R,terrain(:,:,1),Rt,cfg.files.sar_before,cfg.files.terrain);
assert(size(terrain,3)==3,'hill:Bands','Terrain must be elevation,slope,hillshade');
[corridor,Rc] = readgeoraster(cfg.files.corridor);
align_multitemporal_images(before(:,:,1),R,corridor,Rc,cfg.files.sar_before,cfg.files.corridor);
terrainValid=all(isfinite(terrain) & terrain~=cfg.nodata,3);
% Exclude steep terrain conservatively; this is not a complete layover/shadow correction.
valid=va & vb & terrainValid & terrain(:,:,2)<=45 & corridor>0;
[sarChange,sarCandidate] = detect_sar_changes(a,b,valid,cfg.threshold_db);
ndviChange=[]; opticalValid=false(size(valid)); vegetationLoss=false(size(valid));
if isfield(cfg.files,'optical_before') && isfield(cfg.files,'optical_after')
    [oa,Ro] = readgeoraster(cfg.files.optical_before,'OutputType','double');
    [ob,Ro2] = readgeoraster(cfg.files.optical_after,'OutputType','double');
    align_multitemporal_images(before(:,:,1),R,oa(:,:,1),Ro,cfg.files.sar_before,cfg.files.optical_before);
    align_multitemporal_images(oa,Ro,ob,Ro2,cfg.files.optical_before,cfg.files.optical_after);
    [oa,ova] = preprocess_optical(oa,cfg.optical_bands,cfg.nodata);
    [ob,ovb] = preprocess_optical(ob,cfg.optical_bands,cfg.nodata);
    [ndviChange,opticalValid] = calculate_ndvi_change(oa,ob,ova & ovb);
    vegetationLoss=opticalValid & ndviChange < -cfg.ndvi_loss;
end
candidate=generate_change_candidates(sarCandidate,vegetationLoss,opticalValid,valid,terrain(:,:,2),cfg);
[road,Rroad] = readgeoraster(cfg.files.road);
align_multitemporal_images(before(:,:,1),R,road,Rroad,cfg.files.sar_before,cfg.files.road);
roadStats=evaluate_road_overlap(candidate,road>0,R);
stats=calculate_change_statistics(candidate,valid,corridor>0,sarChange);
stats.road_overlap=roadStats; stats.algorithm=cfg.algorithm; stats.segment_id=cfg.segment_id;
stats.processed_at=char(datetime('now','TimeZone','UTC','Format',"yyyy-MM-dd'T'HH:mm:ss'Z'"));
stats.optical_support_pixels=nnz(candidate & vegetationLoss);
stats.experimental=true; stats.warnings=cfg.warnings;
export_analysis_results(cfg,stats,candidate,valid,sarChange,ndviChange,R);
end
