function stats=evaluate_road_overlap(candidate,road,R)
% Raster intersection is a coarse diagnostic; Python performs vector distances/length.
stats.intersection_pixels=nnz(candidate & road);
stats.intersection_area_m2=stats.intersection_pixels*R.CellExtentInWorldX*R.CellExtentInWorldY;
stats.potential_impact=stats.intersection_pixels>0;
stats.confirmed_blockage=false;
end
