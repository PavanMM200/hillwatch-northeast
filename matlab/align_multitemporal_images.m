function align_multitemporal_images(a,Ra,b,Rb,fileA,fileB)
% Export on the same projected grid upstream. Reject misalignment, never silently warp.
assert(isequal(size(a,1),size(b,1)) && isequal(size(a,2),size(b,2)), 'hill:Dimensions','Raster dimensions differ');
assert(isequal(Ra,Rb),'hill:Alignment','Spatial reference or pixel alignment differs');
ia=georasterinfo(fileA); ib=georasterinfo(fileB);
assert(~isempty(ia.CoordinateReferenceSystem) && isequal(ia.CoordinateReferenceSystem,ib.CoordinateReferenceSystem),'hill:Projection','CRS mismatch');
assert(isa(Ra,'map.rasterref.MapCellsReference'),'hill:Projection','Projected metric cells required');
end
