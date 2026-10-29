function tests=test_pipeline
% SIMULATED arrays only. Does not establish scientific accuracy.
tests=functiontests(localfunctions);
end
function test_noDoubleDb(testCase)
[a,v]=preprocess_sar(-10*ones(20,20,2),'dB',-9999);
verifyEqual(testCase,a(10,10,1),-10);verifyTrue(testCase,v(10,10));
end
function test_linearConversion(testCase)
[a,~]=preprocess_sar(.1*ones(20,20,2),'linear',-9999);
verifyEqual(testCase,a(10,10,1),-10,'AbsTol',1e-8);
end
function test_badBands(testCase)
verifyError(testCase,@() preprocess_optical(ones(10,10,4),{'B2','B3','B4','B8'},-9999),'hill:Bands');
end
function test_noData(testCase)
verifyError(testCase,@() preprocess_sar(-9999*ones(20,20,2),'dB',-9999),'hill:NoData');
end
function test_ndviLoss(testCase)
before=ones(10,10,4)*.2;before(:,:,4)=.8;after=ones(10,10,4)*.2;
[delta,valid]=calculate_ndvi_change(before,after,true(10));
verifyEqual(testCase,delta,-.6*ones(10),'AbsTol',1e-8);verifyTrue(testCase,all(valid(:)));
end
function test_incompatibleDimensions(testCase)
verifyError(testCase,@() align_multitemporal_images(ones(10),[],ones(11),[],'',''),'hill:Dimensions');
end
function test_incompatibleReference(testCase)
verifyError(testCase,@() align_multitemporal_images(ones(10),1,ones(10),2,'',''),'hill:Alignment');
end
function test_missingInput(testCase)
verifyError(testCase,@() run_route_analysis('SIMULATED_NONEXISTENT_INPUT.json'),'MATLAB:fileread:cannotOpenFile');
end
function test_fullSyntheticPipeline(testCase)
folder=tempname;mkdir(folder);cleanup=onCleanup(@() rmdir(folder,'s'));
R=maprefcells([500000 500600],[3000000 3000600],[60 60]);
before=-15*ones(60,60,2);after=before;after(20:40,20:40,:)=-3;
terrain=cat(3,1000*ones(60),20*ones(60),150*ones(60));
files=struct();names={'sar_before','sar_after','terrain','corridor','road'};
values={before,after,terrain,ones(60),double(repmat((1:60)>28 & (1:60)<32,60,1))};
for i=1:numel(names)
 files.(names{i})=fullfile(folder,[names{i} '.tif']);
 geotiffwrite(files.(names{i}),single(values{i}),R,'CoordRefSysCode',32646);
end
cfg=struct('files',files,'scenes',struct('acquired_at',{'2026-01-01','2026-01-13'}), ...
 'sar_units','dB','sar_bands',{{'VV','VH'}},'optical_bands',{{'B4','B3','B2','B8'}}, ...
 'epsg',32646,'nodata',-9999,'threshold_db',3,'ndvi_loss',.2,'min_pixels',9, ...
 'min_slope',10,'min_coverage',.85,'output_dir',folder,'warnings',{{'SIMULATED TEST DATA'}}, ...
 'algorithm','experimental-sar-ndvi-v1','segment_id','SIMULATED');
manifest=fullfile(folder,'input.json');fid=fopen(manifest,'w');fwrite(fid,jsonencode(cfg));fclose(fid);
run_route_analysis(manifest);
result=jsondecode(fileread(fullfile(folder,'results.json')));
verifyGreaterThan(testCase,result.changed_pixels,0);
verifyTrue(testCase,isfile(fullfile(folder,'change_mask.tif')));
verifyTrue(testCase,isfile(fullfile(folder,'valid_mask.tif')));
verifyFalse(testCase,result.road_overlap.confirmed_blockage);
end

