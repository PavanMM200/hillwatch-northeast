import bootstrap,argparse,getpass
from sqlalchemy import select
from app.database import Session,User,Audit
from app.auth import hash_password

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('username');parser.add_argument('--role',choices=['Traveller','Reviewer','Road Authority','Administrator'],default='Traveller');args=parser.parse_args()
    password=getpass.getpass('Password (12+ characters): ')
    if len(password)<12 or password!=getpass.getpass('Repeat password: '):raise SystemExit('Password too short or confirmation mismatch')
    with Session() as db:
        if db.scalar(select(User).where(User.username==args.username)):raise SystemExit('User already exists; no changes made')
        user=User(username=args.username,password_hash=hash_password(password),role=args.role);db.add(user);db.flush()
        db.add(Audit(actor='local-administrator',action='create_user',target=user.id,payload={'role':args.role}));db.commit()
    print('Account created. Roles are local application permissions, not proof of government affiliation.')
