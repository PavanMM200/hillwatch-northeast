function [delta,valid]=calculate_ndvi_change(before,after,valid)
den1=before(:,:,4)+before(:,:,1); den2=after(:,:,4)+after(:,:,1);
valid=valid & den1>1e-6 & den2>1e-6;
pre=(before(:,:,4)-before(:,:,1))./max(den1,1e-6);
post=(after(:,:,4)-after(:,:,1))./max(den2,1e-6);
delta=post-pre; delta(~valid)=NaN;
end
