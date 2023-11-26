#!/usr/bin/env python

from datetime import datetime
import argparse
import json
import http.client
from time import ctime, strptime, strftime
from os.path import isfile, dirname, realpath, join, getmtime

API = "api.myquran.com"
FILE_PATH = dirname(realpath(__file__))


class City:
    def __init__(self, id: int, name: str):
        self.__id = id
        self.__name = name

    def getId(self):
        return self.__id

    def getName(self):
        return self.__name


class SholatTimes:
    def __init__(
        self,
        imsak: datetime.time,
        subuh: datetime.time,
        terbit: datetime.time,
        dhuha: datetime.time,
        dzuhur: datetime.time,
        ashar: datetime.time,
        maghrib: datetime.time,
        isya: datetime.time,
    ):
        self.imsak = imsak
        self.subuh = subuh
        self.terbit = terbit
        self.dhuha = dhuha
        self.dzuhur = dzuhur
        self.ashar = ashar
        self.maghrib = maghrib
        self.isya = isya

    # Get Next prayer times
    def getNext(self, this_time: datetime.time):
        sholatTimesList = [
            value
            for idx, value in enumerate(self.__dict__.values())
            if value >= this_time
        ]
        min_idx = 0

        # IF ISYA > THISTIME
        if sholatTimesList:
            min_idx = list(self.__dict__.values()).index(min(sholatTimesList))

        sholatTitle = list(self.__dict__.keys())[min_idx]
        sholatTimes = list(self.__dict__.values())[min_idx]
        return (sholatTitle, sholatTimes)


class DataToday:
    def __init__(
        self,
        lokasi: str,
        daerah: str,
        lat: str,
        lon: str,
        lintang: str,
        bujur: str,
        jadwal: SholatTimes,
        tanggal: str = "",
        tomorrow: bool = False,
    ):
        self.tanggal = tanggal
        self.lokasi = lokasi
        self.daerah = daerah
        self.lat = lat
        self.lon = lon
        self.lintang = lintang
        self.bujur = bujur
        self.jadwal = jadwal
        self.tomorrow = tomorrow

    # Get Prayer times schedule
    def getSholatTimes(self):
        return self.jadwal


# Find City
def cityFind(name: str):
    name = name.strip().lower()
    # Start Connection & Get Response
    response = connectionMake(f"/v1/sholat/kota/cari/{name}", "GET")
    # Check response
    if response.status == 200 and response.reason == "OK":
        response_json = jsonGetResponse(response)
        # Check data
        if response_json["status"] is True:
            response_json_data = response_json["data"]
            cities = [
                City(data["id"], data["lokasi"]) for data in response_json_data
            ]
            return cities
        else:
            return 0
    else:
        return -1


# Choose City
def cityChoose(cities: list, path: str, city_idx: int):
    # Check Python args.cityid value
    if city_idx == -1:
        output = {}
        for i in range(len(cities)):
            output[cities[i].getName()] = i

        # Write Detected Cities to JSON File
        jsonWrite(output, path)
        return 0
    else:
        return cities[city_idx]


# Make Connection to API
def connectionMake(api_url: str, method: str):
    connection = http.client.HTTPSConnection(API)
    connection.request(method, api_url)
    response = connection.getresponse()
    return response


# Check Output JSON file
def fileCheckOutput(path: str, args: argparse.Namespace):
    this_month = f"{datetime.now().year}-{datetime.now().month}"
    # Check the file available
    if isfile(path):
        file_modified = strftime("%Y-%m", strptime(ctime(getmtime(path))))
        # Check File age
        if this_month != file_modified:
            return -2
        else:
            # Get First value from JSON File
            data = next(iter(jsonRead(path)))
            # Check Proper JSON prayer times format
            if data != "status":
                # Check Python args.cityid
                if args.cityid is None:
                    return -3
                else:
                    # First Time Get Monthly Data with args.cityid
                    monthlySchedule = getMonthlySchedule(
                        args.city, path, int(args.cityid)
                    )
                    return monthlySchedule
            else:
                return 3
    else:
        # First Time Get Monthly Data
        monthlySchedule = getMonthlySchedule(args.city, path)
        return monthlySchedule


# Get JSON file from response
def jsonGetResponse(response: http.client.HTTPResponse):
    return json.loads(response.read().decode("utf-8"))


# Read JSON File
def jsonRead(path: str):
    with open(path, "r") as input_files:
        data = input_files.read()
    return json.loads(data)


# Write value to JSON File
def jsonWrite(output: dict, full_path: str):
    with open(full_path, "w") as files:
        json.dump(output, files)


# Make tooltip text for Waybar tooltip
def printTooltip(data: DataToday):
    when = "Hari Ini"
    if data.tomorrow:
        when = "Besok"

    tooltip = (
        f"\uf678 Jadwal Sholat {when}\n"
        f"\uf783 {data.tanggal}\n"
        f"\uf124 {data.lokasi} - "
        f"PROVINSI {data.daerah}\n"
        f"\uf601 Lat: {data.lat} - "
        f"Lon: {data.lon}\n"
        f"\uf601 Lintang: {data.lintang} - "
        f"Bujur: {data.bujur}\n"
        "------------------------------------------------------\n"
        f"Imsak\t: {time_to_str(data.getSholatTimes().imsak)}\n"
        f"Subuh\t: {time_to_str(data.getSholatTimes().subuh)}\n"
        f"Terbit\t: {time_to_str(data.getSholatTimes().terbit)}\n"
        f"Dhuha\t: {time_to_str(data.getSholatTimes().dhuha)}\n"
        f"Dzuhur\t: {time_to_str(data.getSholatTimes().dzuhur)}\n"
        f"Ashar\t: {time_to_str(data.getSholatTimes().ashar)}\n"
        f"Maghrib\t: {time_to_str(data.getSholatTimes().maghrib)}\n"
        f"Isya\t: {time_to_str(data.getSholatTimes().isya)}"
    )
    return tooltip


# Waybar output
def waybarShowOutput(text: str, tooltip: str = "NULL"):
    output = {"text": text, "tooltip": tooltip}
    print(json.dumps(output))


# Get schedule for this month
def getMonthlySchedule(city_name: str, path: str, city_idx: int = -1):
    cities = cityFind(city_name)
    # Check City API
    if cities == -1:
        return -1
    # Check City available
    elif cities == 0:
        return 0
    else:
        city = 0

        # Check Multiple city
        if len(cities) > 1:
            city = cityChoose(cities, path, city_idx)
            if city == 0:
                return -3
        else:
            city = cities[0]

        this_month = str(datetime.now().month)
        this_year = str(datetime.now().year)
        monthly_url = (
            f"/v1/sholat/jadwal/{city.getId()}/{this_year}/{this_month}"
        )
        response = connectionMake(monthly_url, "GET")
        if response.status == 200 and response.reason == "OK":
            response_json = jsonGetResponse(response)
            if response_json["status"] is True:
                # Create JSON File for this month schedule
                jsonWrite(response_json, path)
                return 2
            else:
                return 1
        else:
            return -1


# Convert str to time
def str_to_time(input: str):
    return datetime.strptime(input, "%H:%M").time()


# Convert time to str
def time_to_str(input: datetime.time):
    return input.strftime("%H:%M")


# Main Function
def main():
    filename_output = "jadwale_waybar_output.json"
    full_path = join(FILE_PATH, filename_output)

    # Python Argparse
    parser = argparse.ArgumentParser(
        prog="jadwale",
        description="Get Indonesia Region Prayer Times with myquran.com API",
    )
    parser.add_argument(
        "-c", "--city", type=str, help="City Name", required=True
    )
    parser.add_argument(
        "-i",
        "--cityid",
        nargs="?",
        const="empty",
        help="Use City ID when Multiple Cities Detected",
    )
    main_args = parser.parse_args()

    # Check JSON File
    status = fileCheckOutput(full_path, main_args)

    # CHECK STATUS
    if status == -3:
        message = (
            "Multiple cities are detected!\n"
            "1. Open 'schedule_waybar_output.json' "
            "which is located the same as this script.\n"
            "2. Record the selected city 'ID'.\n"
            "3. Put 'ID' with '-i' argument in the 'exec' section"
            " in the main configuration file 'config.json' Waybar.\n"
            "4. Restart Waybar.\n"
            "For help, see README in this script repository"
        )
        return waybarShowOutput("Multiple cities are Detected!", message)
    elif status == -2:
        return waybarShowOutput(
            "File Outdated",
            "Please delete output JSON file and the script will automatically "
            "fetch new data for this month",
        )
    elif status == -1:
        return waybarShowOutput(
            "API Failed!", "API Not working, please check your connection"
        )
    elif status == 0:
        return waybarShowOutput(
            "City Not Found",
            "City Not Available, change your city name argument",
        )
    elif status == 1:
        return waybarShowOutput("Schedule Not Found")

    # JSON File Ready to Process
    elif status == 2 or status == 3:
        data = jsonRead(full_path)["data"]

        # Custom Time variable
        this_time = datetime.now().time()
        tomorrow_day = datetime.now().day
        today_day = tomorrow_day - 1
        tomorrow = False

        # IF THISTIME > ISYA THEN SHOW TOMORROW DATA
        if this_time >= str_to_time(data["jadwal"][today_day]["isya"]):
            today_day = tomorrow_day
            tomorrow = True

        # Prayer Times Object
        tanggal = data["jadwal"][today_day]["tanggal"]
        prayer_times_data = DataToday(
            data["lokasi"],
            data["daerah"],
            data["koordinat"]["lat"],
            data["koordinat"]["lon"],
            data["koordinat"]["lintang"],
            data["koordinat"]["bujur"],
            SholatTimes(
                str_to_time(data["jadwal"][today_day]["imsak"]),
                str_to_time(data["jadwal"][today_day]["subuh"]),
                str_to_time(data["jadwal"][today_day]["terbit"]),
                str_to_time(data["jadwal"][today_day]["dhuha"]),
                str_to_time(data["jadwal"][today_day]["dzuhur"]),
                str_to_time(data["jadwal"][today_day]["ashar"]),
                str_to_time(data["jadwal"][today_day]["maghrib"]),
                str_to_time(data["jadwal"][today_day]["isya"]),
            ),
            tanggal,
            tomorrow,
        )

        # Get Next Prayer Time
        (
            nextSholatTitle,
            nextSholatTime,
        ) = prayer_times_data.getSholatTimes().getNext(this_time)

        # Create tooltip
        tooltip = printTooltip(prayer_times_data)

        # Show Next prayer time and tooltip
        return waybarShowOutput(
            f"{nextSholatTitle.title()}, {time_to_str(nextSholatTime)}", tooltip
        )


main()
