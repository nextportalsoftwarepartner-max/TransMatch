# flake8: noqa: E501

import psycopg2
import logger
from db_manager import connect_db, hash_password  # Use db_manager functions

logger.logger.info("[staff_manager] : Menu initiation")


# Function to insert a new staff user
def insert_staff(num_login_id, name, password, email, contact, address1, address2, address3, address4, supervisor_id, created_by):
    logger.logger.info("[staff_manager] : Executing the INSERT operation")

    """Insert a new staff user into TM_MST_USER"""
    hashed_pw = hash_password(password)  # Use hash_password from db_manager

    query = """
    INSERT INTO TM_MST_USER (
        VCH_LOGIN_ID, VCH_USER_NAME, VCH_PASSWORD, VCH_EMAIL, VCH_CONTACT,
        VCH_ADDRESS_1, VCH_ADDRESS_2, VCH_ADDRESS_3, VCH_ADDRESS_4,
        NUM_SUPERVISOR_ID, CHR_ACTIVE_IND, DTT_LAST_LOGIN_TIME, 
        NUM_CREATED_BY, DTT_CREATED_AT, NUM_UPDATED_BY, DTT_UPDATED_AT
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Y', NULL, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur', NULL, NULL)
    RETURNING VCH_LOGIN_ID;
    """

    conn = connect_db()  # Use db_manager's connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, (num_login_id, name, hashed_pw, email, contact, address1, address2, address3, address4, supervisor_id, created_by))
            staff_id = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            return staff_id[0] if staff_id else None  # Ensure we return a valid ID
        except psycopg2.Error as e:
            print(f"❌ Database Error: {e}")
            return None
    return None


# Function to update staff details
def update_staff(num_login_id, name, email, contact, address1, address2, address3, address4, updated_by):
    logger.logger.info("[staff_manager] : Executing the UPDATE operation")

    """Update staff details"""
    query = """
    UPDATE TM_MST_USER
    SET VCH_USER_NAME = %s, VCH_EMAIL = %s, VCH_CONTACT = %s,
        VCH_ADDRESS_1 = %s, VCH_ADDRESS_2 = %s, VCH_ADDRESS_3 = %s, VCH_ADDRESS_4 = %s,
        NUM_UPDATED_BY = %s, DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
    WHERE NUM_LOGIN_ID = %s;
    """

    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, (name, email, contact, address1, address2, address3, address4, updated_by, num_login_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except psycopg2.Error as e:
            print(f"❌ Database Error: {e}")
            return False
    return False


# Function to delete staff
def delete_staff(num_login_id):
    logger.logger.info("[staff_manager] : Executing the DELETE operation")

    """Delete a staff user"""
    query = "DELETE FROM TM_MST_USER WHERE NUM_LOGIN_ID = %s;"

    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, (num_login_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except psycopg2.Error as e:
            print(f"❌ Database Error: {e}")
            return False
    return False


# Insert a new staff user (Test)
new_staff_id = insert_staff(
    "superuser", "SUPER USER / ADMINISTRATOR", "@@TransMatch01", "alanchian93@gmail.com", 
    "0189999999", "super user add1", "super user add2", "51100", "Kuala Lumpur", None, None
)
if new_staff_id:
    print(f"✅ Inserted Staff ID: {new_staff_id}")
else:
    print("❌ Staff Insertion Failed")