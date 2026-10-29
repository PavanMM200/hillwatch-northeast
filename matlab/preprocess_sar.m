function [filtered,valid]=preprocess_sar(image,units,nodata)
valid=all(isfinite(image) & image~=nodata,3);
if strcmp(units,'linear')
    valid=valid & all(image>0,3); image=10*log10(max(image,realmin));
else
    assert(strcmp(units,'dB'),'hill:Units','SAR units must be explicit dB or linear');
end
assert(any(valid(:)),'hill:NoData','No valid SAR pixels');
filtered=zeros(size(image));
% Median 3x3 reduces isolated speckle while preserving edges better than mean blur.
% Erode validity so filtering cannot invent support at missing-data boundaries.
for k=1:size(image,3)
    band=image(:,:,k); band(~valid)=0; filtered(:,:,k)=medfilt2(band,[3 3],'symmetric');
end
valid=imerode(valid,ones(3));
end
