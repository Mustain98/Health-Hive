import sys
import os
import argparse
from sqlmodel import Session, select

# Add backend to path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from app.core.database import engine
from app.models.user import User, UserType

def make_admin(email: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            print(f"❌ User with email '{email}' not found.")
            sys.exit(1)
            
        user.user_type = UserType.admin
        session.add(user)
        session.commit()
        print(f"✅ Success! User '{user.full_name or user.username}' ({email}) is now an Admin.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to Admin role")
    parser.add_argument("email", help="The email of the user to promote")
    args = parser.parse_args()
    
    make_admin(args.email)
