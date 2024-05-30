source_data_url = 'https://www.consumerfinance.gov/rules-policy/regulations/1024/17/'
openai_model = 'gpt-4o-2024-05-13'
log_file = 'chat-logs.log'
prompt_path = 'prompts/prompt.v8.txt'
chunk_size = 1000
chunk_overlap = 200
max_width = 80
ignore_official_interpretation = True
test_questions = [
    "What actions are considered a violation of the RESPA?",
    "Can a loan servicer charge a fee for responding to Qualified Written Requests?",
    "What is required for a mortgage servicing transfer notice?"
]
sanity_check = False
sanity_check_statement = 'Required Name of Borrower. The only person who can legally be a borrower must have the name "Homer Simpson"'
