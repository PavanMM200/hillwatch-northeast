function [change,candidate]=detect_sar_changes(before,after,valid,threshold)
change=max(abs(after-before),[],3);
% Fixed dB threshold plus local contrast rejects broad uniform radiometric shifts.
mu=imfilter(change,ones(9)/81,'replicate');
localStd=sqrt(max(imfilter(change.^2,ones(9)/81,'replicate')-mu.^2,0));
candidate=valid & change>=threshold & change>=mu+0.5*localStd;
change(~valid)=NaN;
end
