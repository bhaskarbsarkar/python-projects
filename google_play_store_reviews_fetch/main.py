from google_play_scraper import Sort, reviews
import pandas as pd
import sys # Import sys for better error handling output

def fetch_reviews(app_id, lang='en', country='us', num_reviews=100, filter_score_with=None):
    """
    Fetch reviews from the Google Play Store for a given app.

    Args:
        app_id (str): The app ID of the application.
        lang (str): The language code for the reviews.
        country (str): The country code for the reviews.
        num_reviews (int): The number of reviews to fetch.

    Returns:
        list: A list of dictionaries containing review data.
    """

    # Fetch reviews
    result, _ = reviews(
        app_id,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=num_reviews,
        filter_score_with=filter_score_with
    )

    return result

if __name__ == "__main__":

    app_id = "com.jpl.jiomart"
    country = "in"
    num_reviews = 10000
    app_name = "jiomart"
    
    for n in range(5):
        output_excel_file = f'app_reviews_data_files/{app_name}_reviews_10k_score_{n+1}.xlsx'
        reviews_data = fetch_reviews(app_id, country=country, num_reviews=num_reviews, filter_score_with=n+1)
        print(f"# of Reviews Fetched for score {n+1} : {len(reviews_data)}")
        # Convert the list of dictionaries to a pandas DataFrame
        df = pd.DataFrame(reviews_data)
        # print(f"Converted data to DataFrame with shape: {df.shape}")

        # Save the DataFrame to an Excel file
        try:
            df.to_excel(output_excel_file, index=False, engine='openpyxl')
            print(f"Successfully saved DataFrame to {output_excel_file}")
        except Exception as e:
            print(f"Error writing DataFrame to Excel file {output_excel_file}: {e}")

    # print(f"Rating: {review['score']}")
    # print(f"Date: {review['at']}")
    # print("-" * 40)