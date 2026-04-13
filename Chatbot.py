from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

chathistory=[
    SystemMessage(content='You are a very helpful AI assistant')
]

model=ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite") 
while True:
    user_input=input("You :  ")
    chathistory.append(HumanMessage(content=user_input))
    if user_input == 'exit':
        break
    result = model.invoke(chathistory)
    chathistory.append(AIMessage(content=result.content))
    print("AI :  ",result.content)
print(chathistory)