"""Private terminal configuration; never send secrets to the website or logs."""
import bootstrap
import getpass, json, os, re, shutil, sys
from pathlib import Path
from dotenv import dotenv_values

def ask(label,default='',secret=False):
    suffix=' [configured; Enter to retain]' if secret and default else f' [{default}]' if default else ''
    value=(getpass.getpass if secret else input)(label+suffix+': ').strip()
    value=value or default
    if '\n' in value or '\r' in value:raise ValueError('Multiline values are not accepted')
    return value
def main():
    path=bootstrap.ROOT/'.env';config=dict(dotenv_values(path)) if path.exists() else {}
    print('Hillwatch private setup. Secrets are hidden. Do not paste private JSON keys; enter a local path.')
    print(f'Python {sys.version.split()[0]}. Network and paid Google API checks will run after configuration.')
    fields=[('GOOGLE_CLOUD_PROJECT','Google Cloud project ID','',False),
      ('MAPS_BROWSER_KEY','Maps JavaScript browser key','',True),('MAPS_ROUTES_KEY','Separate backend Routes API key','',True),
      ('MAPS_APIS_ENABLED','Maps JavaScript and Routes APIs enabled? true/false','false',False),
      ('MAPS_BILLING_CONFIRMED','Billing configured? true/false','false',False),
      ('ALLOWED_ORIGINS','Allowed browser origins (comma-separated)','http://localhost:5173,http://localhost:8080',False),
      ('MAPS_BROWSER_RESTRICTIONS','Browser key HTTP referrer restrictions','',False),
      ('MAPS_SERVER_RESTRICTIONS','Backend key API/IP restrictions','',False),
      ('EE_PROJECT','Earth Engine Cloud project ID','',False),('EE_AUTH_METHOD','EE authentication: local / adc / service_account','local',False),
      ('GOOGLE_APPLICATION_CREDENTIALS','ADC/service-account JSON path (leave empty for local login)','',False),
      ('EE_SERVICE_ACCOUNT','Service-account email (if applicable)','',False),
      ('EE_API_ENABLED','Earth Engine API enabled? true/false','false',False),
      ('EE_PROJECT_REGISTERED','EE project registered and authorized? true/false','false',False),
      ('MATLAB_EXECUTABLE','MATLAB executable or installation directory',shutil.which('matlab') or '',False),
      ('MATLAB_VERSION','Installed MATLAB version','',False),('MATLAB_METHOD','Execution method: batch / engine','batch',False),
      ('MATLAB_ENGINE_AVAILABLE','MATLAB Engine API for Python installed? true/false','false',False),
      ('MATLAB_WORK_DIR','MATLAB working directory',str(bootstrap.ROOT/'data/matlab'),False),
      ('DATABASE_URL','Database URL','sqlite:///./data/app.sqlite',True)]
    print('Create Maps keys: Google Cloud Console → APIs & Services → Credentials. Enable Maps JavaScript API and Routes API. Restrict browser key by referrer; backend key by API and server IP. See docs/setup.md.')
    print('MATLAB requires Image Processing Toolbox and Mapping Toolbox; Runtime alone cannot run .m files.')
    for key,label,default,secret in fields:config[key]=ask(label,config.get(key) or default,secret)
    for key in ('GOOGLE_CLOUD_PROJECT','EE_PROJECT'):
        if config[key] and not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',config[key]):raise ValueError(f'{key}: invalid project ID')
    if config['EE_AUTH_METHOD'] not in ('local','adc','service_account'):raise ValueError('Unsupported EE method')
    if config['MATLAB_METHOD'] not in ('batch','engine'):raise ValueError('Unsupported MATLAB method')
    executable=Path(config['MATLAB_EXECUTABLE'])
    if config['MATLAB_EXECUTABLE'] and executable.is_dir():config['MATLAB_EXECUTABLE']=str(executable/'bin'/('matlab.exe' if os.name=='nt' else 'matlab'))
    # Single quotes preserve Windows paths and $ characters in dotenv; reject embedded quotes.
    def encode(v):
        if "'" in v:raise ValueError('Single quotes are not accepted in configuration values')
        return "'"+v+"'"
    tmp=path.with_suffix('.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as out:out.write('\n'.join(f'{k}={encode(v)}' for k,v in config.items())+'\n')
    tmp.replace(path)
    print('Saved .env without printing secrets. On Windows protect it with your user-only ACL; do not commit it.')
    if config['EE_AUTH_METHOD']=='local' and ask('Open Earth Engine authentication now? yes/no','no')=='yes':
        import ee;ee.Authenticate()
    elif config['EE_AUTH_METHOD']=='adc':print('If needed run: gcloud auth application-default login')
    from app.integrations import verify
    for name,result in verify().items():print(f"{name}: {result['status']} — {result['message']}")
if __name__=='__main__':main()
