import pandas as pd

keyword = ['healthy']
app = 'zomato'
output_file_name = f'app_reviews_data_files/{app}_filtered_with_keyword_{'_'.join(keyword)}.txt'

filtered_reviews = []

for n in [1,3,4,5]:
    data = pd.read_excel(f'app_reviews_data_files/zomato_reviews_10k_score_{n}.xlsx')

    for review in data['content']:
        if any(word in str(review).lower() for word in keyword):
            filtered_reviews.append(review)

with open(output_file_name, 'a', encoding='utf-8') as f:
    for review in filtered_reviews:
        f.write(review + '\n') 

print(f"Filtered reviews containing keywords {keyword} have been saved to {output_file_name}.")
