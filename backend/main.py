from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from . import db_helper
from . import generic_helper

app = FastAPI()

# Serve frontend static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

@app.get("/")
def home():
    return FileResponse("backend/static/home.html")

inprogress_orders = {}

# Helper to ensure inprogress_orders is loaded from DB if not in memory
def get_inprogress_order(session_id):
    if session_id not in inprogress_orders:
        order = db_helper.load_inprogress_order(session_id)
        if order:
            inprogress_orders[session_id] = order
    return inprogress_orders.get(session_id)

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()

    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']
    session_id = generic_helper.extract_session_id(output_contexts[0]["name"])

    intent_handler_dict = {
        'order.add - context: ongoing-order': add_to_order,
        'order.remove - context: ongoing-order': remove_from_order,
        'order.complete - context: ongoing-order': complete_order,
        'track.order - context: ongoing-tracking': track_order
    }

    return intent_handler_dict[intent](parameters, session_id)

def save_to_db(order: dict):
    next_order_id = db_helper.get_next_order_id()

    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if rcode == -1:
            return -1

    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id

def complete_order(parameters: dict, session_id: str):
    order = get_inprogress_order(session_id)
    if not order:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. Please place a new order again."
        else:
            order_total = db_helper.get_total_order_price(order_id)
            fulfillment_text = (
                f"Awesome. We have placed your order. "
                f"Here is your order id # {order_id}. "
                f"Your order total is {order_total} which you can pay at the time of delivery!"
            )
        if session_id in inprogress_orders:
            del inprogress_orders[session_id]
        db_helper.delete_inprogress_order(session_id)

    return JSONResponse(content={"fulfillmentText": fulfillment_text})

def add_to_order(parameters: dict, session_id: str):
    food_items = parameters["food-item"]
    quantities = parameters["number"]

    if len(food_items) != len(quantities):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        new_food_dict = dict(zip(food_items, quantities))
        order = get_inprogress_order(session_id)
        if order:
            order.update(new_food_dict)
            inprogress_orders[session_id] = order
        else:
            inprogress_orders[session_id] = new_food_dict

        db_helper.save_inprogress_order(session_id, inprogress_orders[session_id])

        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})

def remove_from_order(parameters: dict, session_id: str):
    order = get_inprogress_order(session_id)
    if not order:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })

    food_items = parameters["food-item"]
    current_order = order

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]

    fulfillment_text = ""
    if removed_items:
        fulfillment_text += f"Removed {', '.join(removed_items)} from your order!"
    if no_such_items:
        fulfillment_text += f" Your current order does not have {', '.join(no_such_items)}."

    if not current_order:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    inprogress_orders[session_id] = current_order
    db_helper.save_inprogress_order(session_id, current_order)

    return JSONResponse(content={"fulfillmentText": fulfillment_text})

def track_order(parameters: dict, session_id: str):
    order_id = int(parameters['order_id'])
    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})
