from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler

from datetime import datetime
import datetime as dt
import os
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

Token = os.getenv('Token')
Botname = '@workshopschedulebot'
CalendarID = os.getenv('CalendarID')

start_times = [
  '0730', '0815', '0830', '0915', '1030', '1115',
  '1300', '1345', '1500', '1545', '1630',
]
end_times = [
  '0815', '0830', '0915', '1000', '1115', '1200',
  '1345', '1430', '1545', '1630', '1715'
]
locations = [
  'UNKNOWN LOCATION', 'Location 1', 'Location 2', 'Location 3', 'Location 4'
]

DATE, TIME_START, TIME_END, LOCATION, NAME, COURSE, CONFIRMBOOKING, SHOWBOOKINGS = range(8)

# The API scope you're requesting
SCOPES = ['https://www.googleapis.com/auth/calendar']


def check_existing_event(service, start_datetime, end_datetime, location):
  """Check if an event already exists at the specified time and location."""
  # Convert start and end datetime to the proper format for the API
  start_str = start_datetime.strftime('%Y-%m-%dT%H:%M:%S+08:00')  # Explicit timezone offset for Singapore (UTC+8)
  end_str = end_datetime.strftime('%Y-%m-%dT%H:%M:%S+08:00')  # Explicit timezone offset for Singapore (UTC+8)

  print(f"Checking for existing events from {start_str} to {end_str} at location: {locations[location]}")  # Debugging line

  try:
    # Call the API to get events in the specified time range
    events_result = service.events().list(
      calendarId = CalendarID,
      timeMin = start_str,
      timeMax = end_str,
      timeZone = "Asia/Singapore"
    ).execute()

    # If there are events, check for overlap at the same location
    events = events_result.get('items', [])
    for event in events:
      # Check if the event location matches
      if 'location' in event and event['location'] == locations[location]:
        print(f"Conflict detected! An event already exists at {locations[location]} during this time.")
        return True  # Conflict found

    
    # No conflict found
    print("No clashing events found. Booking event.")
    return False
  
  except HttpError as error:
    print(f"An error occurred while checking for existing events: {error}")
    return False  # Assuming no conflict in case of an error

# Checking for valid date format
def checkdateformat(input_date):
  format = "%d%m%y"
  try:
    b = bool(datetime.strptime(input_date, format))
  except ValueError:
    b = False
  return b


# Check if date is past
def checkdatepast(input_date):
  past = datetime.strptime(input_date, "%d%m%y")
  present = datetime.now()
  return past.date() > present.date()


# Commands (/whatever then the bot will do stuff)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text('Hello! How can I assist you?')


# Define the function to start the booking process
async def bookslot(update: Update, context: ContextTypes.DEFAULT_TYPE):
  print(f'User ({update.message.chat.id}): Started booking.')
  await update.message.reply_text('Which date would you like to book? Put in format DDMMYY. Eg: 311225')
  return DATE


# Handle the user input for the date with validation
async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
  date = update.message.text
  
  # Check if the date format is valid
  if checkdateformat(date):
    # Check if the date is not in the past
    if checkdatepast(date):
      # Store the valid date in context to use later
      context.user_data['date'] = date
      await update.message.reply_text('Date is valid. Please select the start time for the booking.')
      # Define time slots as buttons
      keyboard = [
        [InlineKeyboardButton("Period 0 (0730 - 0815)", callback_data = 0)],
        [InlineKeyboardButton("Period 1 (0815 - 0830)", callback_data = 1),
        InlineKeyboardButton("Period 2 (0830 - 0915)", callback_data = 2)],
        [InlineKeyboardButton("Period 3 (0915 - 1000)", callback_data = 3),
        InlineKeyboardButton("Period 4 (1030 - 1115)", callback_data = 4)],
        [InlineKeyboardButton("Period 5 (1115 - 1200)", callback_data = 5),
        InlineKeyboardButton("Period 6 (1300 - 1345)", callback_data = 6)],
        [InlineKeyboardButton("Period 7 (1345 - 1430)", callback_data = 7),
        InlineKeyboardButton("Period 8 (1500 - 1545)", callback_data = 8)],
        [InlineKeyboardButton("Period 9 (1545 - 1630)", callback_data = 9),
        InlineKeyboardButton("Period 10 (1630 - 1715)", callback_data = 10)],
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)

      # Send buttons for the user to choose a time slot
      await update.message.reply_text('Please select a time slot:', reply_markup = reply_markup)

      return TIME_START  # Transition to the TIME_START state
    else:
      # Date is in the past
      await update.message.reply_text('Cannot put a past date. Please enter a valid date. Eg: 311225')
      return DATE  # Stay in the DATE state
  else:
    # Date format is invalid
    await update.message.reply_text('Date format is invalid. Please enter a valid date. Eg: 311225')
    return DATE  # Stay in the DATE state


# Handle the user input for the start time
async def handle_time_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Store the start period input
  query = update.callback_query
  starting_period = int(query.data)

  # Store the starting period in context to use later
  context.user_data['starting_period'] = starting_period

  await query.message.edit_text(f'Starting period is Period {starting_period}. Please select the ending period for the booking.')

  # Define time slots as buttons
  keyboard = [
    [InlineKeyboardButton("Period 0 (0730 - 0815)", callback_data = '0')],
    [InlineKeyboardButton("Period 1 (0815 - 0830)", callback_data = '1'),
    InlineKeyboardButton("Period 2 (0830 - 0915)", callback_data = '2')],
    [InlineKeyboardButton("Period 3 (0915 - 1000)", callback_data = '3'),
    InlineKeyboardButton("Period 4 (1030 - 1115)", callback_data = '4')],
    [InlineKeyboardButton("Period 5 (1115 - 1200)", callback_data = '5'),
    InlineKeyboardButton("Period 6 (1300 - 1345)", callback_data = '6')],
    [InlineKeyboardButton("Period 7 (1345 - 1430)", callback_data = '7'),
    InlineKeyboardButton("Period 8 (1500 - 1545)", callback_data = '8')],
    [InlineKeyboardButton("Period 9 (1545 - 1630)", callback_data = '9'),
    InlineKeyboardButton("Period 10 (1630 - 1715)", callback_data = '10')],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  
  # Send buttons for the user to choose a time slot
  await query.message.reply_text('Please select a time slot:', reply_markup = reply_markup)

  return TIME_END  # Transition to the TIME_END state


# Handle the user input for the end time with validation
async def handle_time_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Store the end period input
  query = update.callback_query
  ending_period = int(query.data)
  print('Ending period received.')

  # Get the starting period from the context
  starting_period = int(context.user_data.get('starting_period'))

  # Check if the periods are valid (In order)
  if ending_period < starting_period: # Check if the starting period is after ending period
    
    print('Periods are not valid.')
    await query.message.edit_text('Ending period cannot be before the starting period. Please select a valid ending period.')
  
    # Define time slots as buttons
    keyboard = [
      [InlineKeyboardButton("Period 0 (0730 - 0815)", callback_data = '0')],
      [InlineKeyboardButton("Period 1 (0815 - 0830)", callback_data = '1'),
      InlineKeyboardButton("Period 2 (0830 - 0915)", callback_data = '2')],
      [InlineKeyboardButton("Period 3 (0915 - 1000)", callback_data = '3'),
      InlineKeyboardButton("Period 4 (1030 - 1115)", callback_data = '4')],
      [InlineKeyboardButton("Period 5 (1115 - 1200)", callback_data = '5'),
      InlineKeyboardButton("Period 6 (1300 - 1345)", callback_data = '6')],
      [InlineKeyboardButton("Period 7 (1345 - 1430)", callback_data = '7'),
      InlineKeyboardButton("Period 8 (1500 - 1545)", callback_data = '8')],
      [InlineKeyboardButton("Period 9 (1545 - 1630)", callback_data = '9'),
      InlineKeyboardButton("Period 10 (1630 - 1715)", callback_data = '10')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
      
    # Send buttons for the user to choose a time slot
    await query.message.reply_text('Please select a time slot:', reply_markup = reply_markup)
    return TIME_END  # Stay in the TIME_END state
  
  else:
    # Store the ending period in context to use later
    context.user_data['ending_period'] = ending_period

    await query.message.edit_text(f'Ending period is Period {ending_period}. Please select the location for the booking.')
    
    # Define locations as buttons
    keyboard = [
      [InlineKeyboardButton("Location 1", callback_data = '1'),
      InlineKeyboardButton("Location 2", callback_data = '2')],
      [InlineKeyboardButton("Location 3", callback_data = '3'),
      InlineKeyboardButton("Location 4", callback_data = '4')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
      
    # Send buttons for the user to choose a location
    await query.message.reply_text('Please select a location:', reply_markup = reply_markup)

    return LOCATION  # Transition to the LOCATION state


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Store the location input
  query = update.callback_query
  location = int(query.data)
  print('Location received.')

  # Store the starting period in context to use later
  context.user_data['location'] = location

  await query.message.edit_text(f'Location is {locations[location]}')
  await query.message.reply_text('Enter your rank and name. Eg: 3SG Ethan Cole')

  return NAME  # Transition to the NAME state


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Store the name input
  name = update.message.text
  print('Name received.')

  # Store name in context to use later
  context.user_data['name'] = name

  await update.message.reply_text('Enter your course/reason for booking. Eg: BSC, ISC, Works')

  return COURSE # Transition to the COURSE state


async def handle_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Store the name input
  course = update.message.text
  print('Course received.')

  # Store course in context to use later
  context.user_data['course'] = course

  # Get the date, starting and ending periods & location from the context
  date = context.user_data.get('date')
  starting_period = context.user_data.get('starting_period')
  ending_period = context.user_data.get('ending_period')
  location = context.user_data.get('location')

  # Confirmation message + buttons
  printed_date = datetime.strptime(date, '%d%m%y')
  message = f'Booking details:\nDate: {printed_date.strftime("%d %b %Y")}\nTime: {start_times[starting_period]} - {end_times[ending_period]}\nLocation: {locations[location]}'

  await update.message.reply_text(message)

  keyboard = [
    [InlineKeyboardButton("YES", callback_data = 'YES')],
    [InlineKeyboardButton("NO", callback_data = 'NO')],
  ]

  reply_markup = InlineKeyboardMarkup(keyboard)
      
  # Send buttons for the user to choose a location
  await update.message.reply_text('Confirm booking?', reply_markup = reply_markup)

  # End the conversation after the booking is done
  return CONFIRMBOOKING


async def confirmbooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  answer = query.data

  if answer == "YES":
    creds = None

    if os.path.exists("token.json"):
      creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
      else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port = 0)

      with open("token.json", "w") as token:
        token.write(creds.to_json())

    await query.edit_message_text("Checking booking availibility...")
    try:
      service = build("calendar", "v3", credentials = creds)
      
      # Get all the data from the context
      date = context.user_data.get('date')
      starting_period = context.user_data.get('starting_period')
      ending_period = context.user_data.get('ending_period')
      location = context.user_data.get('location')
      name = context.user_data.get('name')
      course = context.user_data.get('course')
      
      # Converting the date and times into ISO format
      date_obj = datetime.strptime(date, '%d%m%y')
      start_time_obj = datetime.strptime(start_times[starting_period], '%H%M').time()
      end_time_obj = datetime.strptime(end_times[ending_period], '%H%M').time()
      
      combined_start_datetime = datetime.combine(date_obj, start_time_obj)
      start_datetime = combined_start_datetime.isoformat()
      combined_end_datetime = datetime.combine(date_obj, end_time_obj)
      end_datetime = combined_end_datetime.isoformat()

      # Check if an event already exists at the same time and location
      if check_existing_event(service, combined_start_datetime, combined_end_datetime, location):
        await query.edit_message_text(f"{locations[location]} has already been booked for that time. Please book another slot.")
        return ConversationHandler.END
      
      # If no conflict, create the event
      await query.edit_message_text("Processing booking...")
      event = {
      "summary": "My Python Event",
      "location": locations[location],
      "description": f"Booked by {name} for {course}",
      "colorId": location,
      "start": {
          "dateTime": start_datetime,
          "timeZone": "Asia/Singapore"
      },
          "end": {
          "dateTime": end_datetime,
          "timeZone": "Asia/Singapore"
      },
      }
        
      event = service.events().insert(
                                      calendarId = CalendarID,
                                      body = event
                                      ).execute()

      print(f"Event created. {event.get('htmlLink')}")
      confirmation_message = f"""
          Your booking has been confirmed!

Booking details:
          Date: {date_obj.strftime("%d %b %Y")}
          Time: {start_times[starting_period]} - {end_times[ending_period]}
          Location: {locations[location]}
          Booked by: {name}
          Course/Reason: {course}

You can view your booking at: {event.get('htmlLink')}"""
      await query.message.edit_text(confirmation_message)
   
    except HttpError as error:
      print("An error occured: ", error)
      
    return ConversationHandler.END

  elif query.data == "NO":
    await query.edit_message_text("Booking terminated.")
    return ConversationHandler.END
  else:
    await query.edit_message_text("Unknown option selected.")
    return ConversationHandler.END


# Define the handler for invalid inputs or cancellations
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text('Processed cancelled.')
  return ConversationHandler.END


async def bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
  print(f'User ({update.message.chat.id}): Viewing Bookings.')
  await update.message.reply_text('Which date would you like to view? Put in format DDMMYY. Eg: 311225')
  return SHOWBOOKINGS

async def show_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
  date = update.message.text
  
  # Check if the date format is valid
  if checkdateformat(date):
    # Check if the date is not in the past
    if checkdatepast(date):
      print('Valid date recieved.')
      creds = None

      if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")

      if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
          creds.refresh(Request())
        else:
          flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
          creds = flow.run_local_server(port = 0)

        with open("token.json", "w") as token:
          token.write(creds.to_json())

      try:
        reply_message = await update.message.reply_text('Obtaining bookings from calendar...')
        service = build('calendar', 'v3', credentials = creds)
        
        utc_plus_8 = dt.timezone(dt.timedelta(hours = 8))
        date = datetime.strptime(date, '%d%m%y')
        time_min = date.replace(hour = 0, minute = 0, second = 0, microsecond = 0, tzinfo = utc_plus_8)
        time_max = date.replace(hour = 23, minute = 59, second = 59, microsecond = 999999, tzinfo = utc_plus_8)

        printed_date = date.strftime("%d %b %Y")

        # Call the API to get the events
        events_result = service.events().list(
            calendarId = CalendarID,
            timeMin = time_min.isoformat(),
            timeMax = time_max.isoformat(),
            timeZone = 'Asia/Singapore',
            singleEvents = True,
            orderBy = 'startTime'
        ).execute()

        events = events_result.get('items', [])
        events_sorted = sorted(events,
                               key = lambda event: (event.get('start', {}).get('dateTime', ''), event.get('location', ''))
                               )

        if not events:
          await reply_message.edit_text(f"No bookings found for {printed_date}.")
          return ConversationHandler.END
          
        message = f"Here are the bookings for {printed_date}:\n\n"

        for event in events_sorted:
          # Extracting event start time and end time
          start = event["start"].get("dateTime", event["start"].get("date"))
          end = event["end"].get("dateTime", event["end"].get("date"))
          
          start = datetime.strptime(start, '%Y-%m-%dT%H:%M:%S%z')
          end = datetime.strptime(end, '%Y-%m-%dT%H:%M:%S%z')
          start_time = start.strftime('%H%M')
          end_time = end.strftime('%H%M')
          location = event.get("location", "No location provided")
          description = event.get("description", "No description provided")

          message += f"Time: {start_time} - {end_time}\n"
          message += f"Location: {location}\n"
          message += f"Description: {description}\n"
          message += "-" * 40 + "\n"

        await reply_message.edit_text(message)
        return ConversationHandler.END

      except HttpError as error:
        print(f"An error occurred: {error}")

    else:
      # Date is in the past
      await update.message.reply_text('Cannot put a past date. Please enter a valid date. Eg: 311225')
      return SHOWBOOKINGS  # Stay in the SHOWBOOKINGS state
  else:
    # Date format is invalid
    await update.message.reply_text('Date format is invalid. Please enter a valid date. Eg: 311225')
    return SHOWBOOKINGS  # Stay in the SHOWBOOKINGS state


# Responses (reads and handles responses, without /whatever)
def handle_response(text: str) -> str:
  processed: str = text.lower()
  if 'hello' in processed:
    return "Hey there!"
  return 'Unknown message.'


# Handles messages from private or groups
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message_type: str = update.message.chat.type
  text: str = update.message.text

  print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

  if message_type == 'group':
    if Botname in text:
      new_text: str = text.replace(Botname, '').strip()
      response: str = handle_response(new_text)
    else:
      return
  else:
    response:str = handle_response(text)

  print('Bot:', response)
  await update.message.reply_text(response)


#Error handling
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
  print(f'Update {update} caused error {context.error}')
  if isinstance(update, Update):
    if update.message:
      print(f"Error Message: {update.message.text}")
    elif update.callback_query:
      print(f"Error Callback Query: {update.callback_query.data}")


def main():
  application = Application.builder().token(Token).build()

  #Commands
  application.add_handler(CommandHandler('start', start))
  
  conversation_handler = ConversationHandler(
    entry_points = [
      CommandHandler("bookslot", bookslot),
      CommandHandler("bookings", bookings),
    ],
    states = {
      DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
      TIME_START: [CallbackQueryHandler(handle_time_start)],
      TIME_END: [CallbackQueryHandler(handle_time_end)],
      LOCATION: [CallbackQueryHandler(handle_location)],
      NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
      COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_course)],
      CONFIRMBOOKING: [CallbackQueryHandler(confirmbooking)],
      SHOWBOOKINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_bookings)],
    },
    fallbacks = [CommandHandler('cancel', cancel)],
  )

  # Add the conversation handler to the application
  application.add_handler(conversation_handler)

  #Messages
  application.add_handler(MessageHandler(filters.TEXT, handle_message))

  #Errors
  application.add_error_handler(error)

  #Polling (Checks for new messages)
  print('Polling...')
  application.run_polling()

if __name__ == '__main__':
  main()
