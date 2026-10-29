function candidate=generate_change_candidates(sar,loss,opticalValid,valid,slope,cfg)
% Optical loss is supporting evidence, never standalone proof of landslide.
% With usable optical data require corroboration; otherwise retain SAR-only candidates.
candidate=sar & (~opticalValid | loss) & valid & slope>=cfg.min_slope;
candidate=bwareaopen(candidate,cfg.min_pixels,8);
end
