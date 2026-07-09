import argparse
import pandas as pd
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_storage.statistics import make_statistics_day, make_statistics_month, make_statistics_electricity_day
from config import *

meses = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"]

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process weather data.')
    parser.add_argument('--date', type=str, help='Date in the format dd/mm/yy', required=False)
    return parser.parse_args()

def load_data():
    return pd.read_csv(HISTORICAL_WEATHER_DIR)
def load_data_electrica():
    return pd.read_csv(ELECTRICITY_DIR_CONSUMPTION,sheet_name="consumption"),pd.read_csv(ELECTRICITY_DIR_PRODUCTION,sheet_name="production")

def filter_data(data, date):
    print(date)
    day =int(date[:2]) 
    month = meses[int(date[3:5]) - 1]
    print(f"Day: {day}, Month: {month}")
    return data[(data['Mes'] ==month) & (data['Dia'] == int(day))],day,month

def make_stats():
    date=input("Enter the date in the format dd/mm/yy: ")
    data = load_data()
    filtered_data,day,month = filter_data(data, date)
    df_day=make_statistics_day(filtered_data,day,month)
    df_month = make_statistics_month(df_day, month)
    data_electrica_consumption,data_electrica_production=load_data_electrica()
    make_statistics_electricity_day([data_electrica_consumption,data_electrica_production])
    


def modify_columns():
    file_path = input("Enter the path to the Excel file: ")
    new_order = input("Enter the new column order, separated by commas: ").split(',')

    # Load the Excel file
    df = pd.read_csv(file_path)

    # Reorder the columns
    df = df[new_order]

    # Save the modified DataFrame back to the Excel file
    df.to_csv(file_path, index=False)

    print("Columns reordered successfully.")
def display_menu():
        print("Select an option:")
        print("1. Process weather data for a specific date")
        print("2. Modify columns")
        print("3. Fill N/A in a column")
        print("4. Convert Excel file to CSV")
        print("5. Exit")

import pandas as pd

def fill_na_in_column():
    file_path = input("Enter the path to the Excel file: ")
    columns = input("Enter the column names to fill N/A, separated by commas: ").split(',')

    # Load the Excel file
    df = pd.read_csv(file_path)

    # Verificar si la columna existe
    # if columns not in df.columns:
    #     print(f"Error: La columna '{columns}' no existe.")
    #     return

    # Convertir la columna a tipo object para evitar problemas de dtype
    df[columns] = df[columns].astype(object)

    # Llenar valores NaN con "N/A"
    df[columns] = df[columns].fillna("N/A")

    # Guardar el DataFrame modificado
    df.to_csv(file_path, index=False)

    print(f"Filled N/A in column '{columns}' successfully.")

def to_csv():
    file_path = input("Enter the path to the Excel file: ")
    output_path = input("Enter the path to save the CSV file: ")

    # Load the Excel file4
    # Convert all sheets to a single DataFrame
    all_sheets = pd.read_excel(file_path, sheet_name=None)
    df = pd.concat(all_sheets.values(), ignore_index=True)
    # Save the DataFrame to a CSV file
    df.to_csv(output_path, index=False)

    print(f"Excel file saved as CSV file successfully.")


def main():
    while True:
        display_menu()
        choice = input("Enter your choice: ")
        if choice == '1':
            make_stats()
            break
        elif choice == '2':
            modify_columns()
            break
        elif choice == '3':
            fill_na_in_column()
            break
        elif choice == '4':
            to_csv()
            break
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()