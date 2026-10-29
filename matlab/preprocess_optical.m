function [image,valid]=preprocess_optical(image,bands,nodata)
assert(isequal(string(bands(:)),["B4";"B3";"B2";"B8"]),'hill:Bands','Expected B4,B3,B2,B8');
assert(size(image,3)==4,'hill:Bands','Four optical bands required');
% Earth Engine SCL mask already removed cloud/shadow/snow before export.
valid=all(isfinite(image) & image~=nodata & image>=0,3);
image=image/10000;
end
