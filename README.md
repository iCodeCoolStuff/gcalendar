# gcalendar

A command line tool for Google Calendar that uses Python

## Getting Started

### Prerequisites

The latest version of [Python](https://www.python.org/downloads/)

### Installing

1. `git clone (this repository)`
2. Open the command line and change to the directory of where you cloned this repository'.
3. (Optional) set up a virtaul environment. Do `pip install virtualenv` if you do not already have it installed. Otherwise, go to the project directory and type in `virtualenv venv`. This will create a virtual environment and will be ignored when committing.
4. Type in `pip install --editable .`.
5. Do `gcalendar --help` to check if you installed it correctly.

### Starting Google Calendar API

1. Go to [this website](https://developers.google.com/calendar/quickstart/python)
2. Scroll down and click on the big blue button that says "Enable The Google Calendar Api"
3. Follow the steps to set it up.
4. Copy your client_id and your client_secret.
5. Open the command line and type in `gcalendar authorize -ci (your client_id) -cs (your client_secret)`.
6. Allow quickstart access to your Google Calendar.
7. You are now set up.

### Usage

Supported Commands:
```
  authorize       Authorizes credentials for Google Api
  copy            Copies a schedule from a day to another day
  delete          Delete events from a specific day
  list            List events from a file or day
  list_schedules  Lists all of the schedules that are currently saved
  spawn           Spawns an instance of Google Calendar in a web browser
  save            Save a schedule of events to a file
  upload          Upload events from a file to a specific date
```

Do `gcalendar (command) --help` for more info.

## Running tests

Do `python -m unittest (test_file)`. Each one starts with a `test_` prefix.

## Dependencies

* [Google Api Client](https://developers.google.com/api-client-library/python/) - Calendar API
* [click](https://click.palletsprojects.com/en/7.x/) - Command line tool
* [oauth2](https://github.com/googleapis/oauth2client) - Used for authorizing applications

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
