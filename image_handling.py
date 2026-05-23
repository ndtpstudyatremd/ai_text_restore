import base64

def get_ai_image_description(groq_client, image_bytes, system_prompt):
    image_b64 = base64.b64encode(image_bytes.read()).decode("utf-8")

    response = groq_client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt
                    },
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content