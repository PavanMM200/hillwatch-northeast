function stats=calculate_change_statistics(candidate,valid,corridor,change)
stats.valid_fraction=nnz(valid & corridor)/max(nnz(corridor),1);
stats.changed_pixels=nnz(candidate);
stats.candidate_components=bwconncomp(candidate,8).NumObjects;
if any(valid(:)), stats.mean_absolute_change_db=mean(change(valid),'omitnan');
else, stats.mean_absolute_change_db=[]; end
end
