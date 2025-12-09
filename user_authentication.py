from db_manager import connect_db, hash_password, verify_password


def authenticate_user(login_id, password):
    """Authenticate user login and return user ID & role"""
    query = """
    SELECT NUM_LOGIN_ID, VCH_PASSWORD, num_role_id
    FROM TM_MST_USER
    WHERE NUM_LOGIN_ID = %s;
    """
    
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute(query, (login_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and verify_password(user[1], password):  # Check password match
            return {"login_id": user[0], "role_id": user[2]}
    
    return None  # Return None if authentication fails
