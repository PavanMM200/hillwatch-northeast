function export_analysis_results(cfg,stats,candidate,valid,change,ndvi,R)
% Validity is a separate georeferenced output; zero is not evidence where invalid.
mask=uint8(candidate); mask(~valid)=0;
geotiffwrite(fullfile(cfg.output_dir,'change_mask.tif'),mask,R,'CoordRefSysCode',cfg.epsg);
geotiffwrite(fullfile(cfg.output_dir,'valid_mask.tif'),uint8(valid),R,'CoordRefSysCode',cfg.epsg);
view=min(change/10,1);view(~isfinite(view))=0;
imwrite(view,fullfile(cfg.output_dir,'sar_change.png'));
if ~isempty(ndvi)
    view=(max(min(ndvi,1),-1)+1)/2; view(~isfinite(view))=0;
    imwrite(view,fullfile(cfg.output_dir,'ndvi_change.png'));
    geotiffwrite(fullfile(cfg.output_dir,'ndvi_change.tif'),single(ndvi),R,'CoordRefSysCode',cfg.epsg);
end
fid=fopen(fullfile(cfg.output_dir,'results.json'),'w');
assert(fid~=-1,'hill:Output','Cannot create results'); cleaner=onCleanup(@() fclose(fid));
fwrite(fid,jsonencode(stats),'char');
end
