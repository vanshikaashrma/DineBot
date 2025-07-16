import mysql.connector
from dotenv import load_dotenv
import os
import json

load_dotenv()

cnx = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

# Function to call the MySQL stored procedure and insert an order item
def insert_order_item(food_item, quantity, order_id):
    try:
        cursor = cnx.cursor()

        # Calling the stored procedure
        cursor.callproc('insert_order_item', (food_item, quantity, order_id))

        # Committing the changes
        cnx.commit()

        # Closing the cursor
        cursor.close()

        print("Order item inserted successfully!")

        return 1

    except mysql.connector.Error as err:
        print(f"Error inserting order item: {err}")

        # Rollback changes if necessary
        cnx.rollback()

        return -1

    except Exception as e:
        print(f"An error occurred: {e}")
        # Rollback changes if necessary
        cnx.rollback()

        return -1

# Function to insert a record into the order_tracking table
def insert_order_tracking(order_id, status):
    cursor = cnx.cursor()

    # Inserting the record into the order_tracking table
    insert_query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
    cursor.execute(insert_query, (order_id, status))

    # Committing the changes
    cnx.commit()

    # Closing the cursor
    cursor.close()

def get_total_order_price(order_id):
    cursor = cnx.cursor()

    # Executing the SQL query to get the total order price
    query = f"SELECT get_total_order_price({order_id})"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()[0]

    # Closing the cursor
    cursor.close()

    return result

# Function to get the next available order_id
def get_next_order_id():
    cursor = cnx.cursor()

    # Executing the SQL query to get the next available order_id
    query = "SELECT MAX(order_id) FROM orders"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()[0]

    # Closing the cursor
    cursor.close()

    # Returning the next available order_id
    if result is None:
        return 1
    else:
        return result + 1

# Function to fetch the order status from the order_tracking table
def get_order_status(order_id):
    cursor = cnx.cursor()

    # Executing the SQL query to fetch the order status
    query = f"SELECT status FROM order_tracking WHERE order_id = {order_id}"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()

    # Closing the cursor
    cursor.close()

    # Returning the order status
    if result:
        return result[0]
    else:
        return None

def save_inprogress_order(session_id, order_dict):
    cursor = cnx.cursor()
    order_json = json.dumps(order_dict)
    query = "REPLACE INTO inprogress_orders (session_id, order_json) VALUES (%s, %s)"
    cursor.execute(query, (session_id, order_json))
    cnx.commit()
    cursor.close()

def load_inprogress_order(session_id):
    cursor = cnx.cursor()
    query = "SELECT order_json FROM inprogress_orders WHERE session_id = %s"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    cursor.close()
    if result:
        return json.loads(result[0])
    return None

def delete_inprogress_order(session_id):
    cursor = cnx.cursor()
    query = "DELETE FROM inprogress_orders WHERE session_id = %s"
    cursor.execute(query, (session_id,))
    cnx.commit()
    cursor.close()


if __name__ == "__main__":
    # print(get_total_order_price(56))
    # insert_order_item('Samosa', 3, 99)
  
    # insert_order_tracking(99, "in progress")
    print(get_next_order_id())
