import os
from openai import OpenAI

client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")

def call_openai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a Expert in Finding Compliance Standards for new Product that are to be launched."},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"

def call_openai_structured(prompt,structured_response):
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=structured_response,
            messages=[{"role": "system", "content": "You are a Expert in Finding Compliance Standards for new Product that are to be launched."},
                      {"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"