import os
import pickle
import pandas as pd
import datetime
import numpy as np
import click


def load_error_data(city, provider, error_path):
    """Loads the error file and returns the error data for the specific city and provider given in the query 

    :param city: city for which the weather forecast is for
    :type string
    :param provider: provider for which the weather forecast is for
    :type string
    :param error_path: path to error data
    :type string
    :return: dataFrame containing all errors for a city and provider
    """
    # load the file
    complete_errorpath = os.path.join(error_path, "errorfile.csv")
    with open(complete_errorpath,'rb') as f:
        error_data = pd.read_csv(f)
        
    # get rows with the correct city and provider
    error_data_city = error_data[error_data['city']==city]
    
    return error_data_city[error_data_city['Provider']==provider]
    

def get_score(dwd_data, forecast_data, provider):
    """Gets a single pandas table rows of the dwd data and forecast_data and
    returns scalar error-values for each column

    :param dwd_data:  single row of a pandas table with columns = ['Provider','ref_date','city','pred_offset','Station ID', 'Date', 'Quality Level', 'Air Temperature', \
    'Vapor Pressure', 'Degree of Coverage', 'Air Pressure', 'Rel Humidity', \
    'Wind Speed', 'Max Air Temp', 'Min Air Temp', 'Min Groundlvl Temp', \
    'Max Wind Speed', 'Precipitation', 'Precipitation Ind', 'Hrs of Sun', \
    'Snow Depth']
    :type: dataframe
    :param forecast_data: single row of a pandas table with columns = ['Provider','ref_date','city','pred_offset','Station ID', 'Date', 'Quality Level', 'Air Temperature', \
    'Vapor Pressure', 'Degree of Coverage', 'Air Pressure', 'Rel Humidity', \
    'Wind Speed', 'Max Air Temp', 'Min Air Temp', 'Min Groundlvl Temp', \
    'Max Wind Speed', 'Precipitation', 'Precipitation Ind', 'Hrs of Sun', \
    'Snow Depth']
    :type: dataframe
    :return:dictionary of differences between dwd and forecast (dwd-forecast)
    for the columns/keys Air Temperature, Rel Humidity, Wind Speed, Max Air Temp, Min Air Temp
    Precipitation, Snow Depth
    openweathermap nan = 0 and rain in millimeters
    accuweather - rain in millimeters. only supplies min and max temperature
    weatherdotcom - gives rain only for today
    """

    temp_min_max = ['Max Air Temp', 'Min Air Temp']
    errors = {}
    errors['Air Temperature'] = (dwd_data['Air Temperature']-forecast_data['Air Temperature']).values

    if provider =='weatherdotcom':
        errors['Precipitation'] = None
        errors['Min Air Temp'] = None
        errors['Max Air Temp'] = None
    else:
        errors['Precipitation'] = (dwd_data['Precipitation']-forecast_data['Precipitation'].fillna()).values
        errors['Max Air Temp'] = (dwd_data['Max Air Temp']-forecast_data['Max Air Temp']).values
        errors['Min Air Temp'] = (dwd_data['Min Air Temp']-forecast_data['Min Air Temp']).values

    return errors

def get_data_dwd(city,start_date, end_date,dwd_path):
    """reads in the city, date and dwd_path and returns the data queried from the dwd path
    
    :param city: city for which the weather forecast is for
    :type string
    :param date: date for which the weather forecast is for
    :type datetime
    :param dwd_path: path to the database repository (where the file weather_loading.py is)
    :type string
    :return: dataFrame containing relevant dwd data
    """
    curr_wd = os.getcwd()
    os.chdir(dwd_path)
            
    import weather_loading as wl
    dataFrame = wl.load_dataframe(city, str(start_date)[:-9].replace('-', ''), str(end_date)[:-9].replace('-', ''),True)

    os.chdir(curr_wd)
    return dataFrame


def get_date_forecast(city, provider, date, offset, forecast_dataframe):
    """Returns the row of the forecast_dataframe corresponding to the given city, provider, date
    and offset.

    :param city: city name
    :type string
    :param provider: provider name
    :type string
    :param date: date of the day for which to get the forecast
    :type datetime (python package datetime.datetime)
    :param offset: day of forecast minus day where forecast was made
    :type int
    :param forecast_dataframe:
    :type pandas dataframe
    :return: pandas dataframe row of forecast_dataframe corresponding to the
    given parameters
    """
    data_city = forecast_dataframe[forecast_dataframe['city']==city]
    data_prov = data_city[data_city['Provider']==provider]
    data_date = data_prov[data_prov['ref_date']==date]

    if provider == 'openweathermap':
        data_date[(data_date['pred_offset'].values-data_date['ref_date'])]
        
    return data_date[data_date['pred_offset'] == offset]



def update_errors(end_date, forecast_path="", dwd_path="", errors_path="", start_date='2015-06-01'):
    """adds to the errors file error entry for a specific date

    :param date: date for which we want to calculate the errors
    :type datetime (python package datetime.datetime)
    :param forecast_path: path to the forecast master dataframe
    :type string
    :param dwd_path: path to dwd downloaded data
    :type string
    :param errors_path: path to the errors file that should be updated
    :type string
    :return:
    """

    dates = pd.date_range(start_date, end_date, freq='D')
    complete_errorpath = os.path.join(errors_path, "errorfile.csv")

    if os.path.exists(complete_errorpath):
        print("Found errorfile, loading it...")
        errorData = pd.read_csv(os.path.join(errors_path,"errorfile.csv"))
        print("Successfully loaded the errorfile from " + complete_errorpath)
    else:
        print("Didn't find an error file, creating one...")
        errorData = pd.DataFrame(columns=
                    np.array(['Provider', 'city','offset', 'date', 'Air Temperature', \
                        'Max Air Temp', 'Min Air Temp', 'Precipitation']))
        print("I created an errors dataframe.")

    citylist = ['berlin','hamburg','bremen','stuttgart']
    providerlist = ['accuweather', 'openweathermap', 'weatherdotcom']

    for city in citylist:
        dwdData = get_data_dwd(city,start_date, end_date,dwd_path)
        dwdData = dwdData[list(dwdData.keys())[0]]
        for date in dates:
            for provider in providerlist:
                forecastData = load_forecasts(city, provider, date, forecast_path)
                offset_range = 7
                for offset in range(offset_range):
                    date_forecast = forecastData[forecastData['pred_offset'].astype(int) == int(offset)]
                    scores = get_score(dwdData, date_forecast)
                    scores['offset'] = offset
                    scores['city'] = city
                    #scores['date'] = date
                    scores['Provider']

                    errorData.append(scores,ignore_index=True)

    errorData.to_csv(complete_errorpath)
    print("Saved error data to " + complete_errorpath)


def load_forecasts(city, provider, date, forecast_path):
    """reads in the cierror_mat = np.zeros(7,4)
for offset in np.arange(7):
    for value in np.arange(4):
        offset_mask = mat[:,0] == offset
        error_mat[offset,value] = np.average(mat[offset_mask,value+1],axis=0)ty, provider, date and forecast_path and returns the data queried from the forecast path

    :param city: city for which the weather forecast is for
    :type string
    :param provider: provider for which the weather forecast is for
    :type string
    :param date: date for which the weather forecast is for, e.g. '2015-06-29'
    :type datetime
    :param dwd_path: path to the corresponding dwd data
    :type string
    :return: dataFrame containing relevant dwd data
    """
    
    # load the file
    with open(forecast_path,'rb') as f:
        data = pickle.load(f)
        
    # get rows with the correct city, provider and date
    data_city = data[data['city']==city]
    data_provider = data_city[data_city['Provider']==provider]

    if provider != 'openweathermap':
        # cut the time
        data_provider['Date'] = data_provider['Date'].map(cut_time,na_action='ignore')
        data_provider['ref_date'] = data_provider['ref_date'].map(cut_time,na_action='ignore')

    else:
        data_provider['ref_date'] = data_provider['ref_date'].map(cut_time,na_action='ignore')
        data_provider['Date'] = data_provider['pred_offset'].map(cut_time, na_action='ignore')
        data_provider['pred_offset'] = data_provider['Date'] - data_provider['ref_date']
    
    return data_provider[data_provider['Date'] == date]

    
def cut_time(date_frmt):
    """ cuts the time of the datetime format
    
    :param date_frmt: date in the format %Y-%m-%d %H:%M:%S
    :type datetime
    :return: date in the format %Y-%m-%d
    """
    frmt = '%Y-%m-%d'
    return datetime.datetime.strptime(date_frmt.strftime(frmt),frmt)

@click.option("--errors_path", type=click.STRING, default="")
def main(errors_path):
    citylist = ['berlin','hamburg','bremen','stuttgart']
    providerlist = ['accuweather', 'openweathermap', 'weatherdotcom']

    errors = np.zeros((len(providerlist), len(citylist), 7))
    for i, provider in enumerate(providerlist):
        for j, city in enumerate(citylist):
            diff = load_error_data(city, provider, errors_path).values

            mat = diff['offset','Air Temperature'].values.squeeze()

            errors[i,j,:] = diff

if __name__ == '__main__':
    main()

# sample code for the error computation
overall_mean_square_error = np.zeros((7,4,3)) # offset x values x providers
mat = diff['offset', 'Air Temperature', 'Max Air Temp', 'Min Air Temp', 'Precipitation'].as_matrix()
error_mat = np.zeros(7,4)
mean_square_error = np.zeros((7,4))

for offset in np.arange(7):
    for value in np.arange(4):
        offset_mask = mat[:,0] == (offset+1)
        error_mat[offset,:] = np.average(mat[offset_mask,value+1],axis=0)
        mean_square_error = np.linalg.norm(mat[offset_mask,value+1], axis=0)
    
overall_mean_square_error[:,:,provider_idx] = mean_square_error
