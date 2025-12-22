from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from tools import menu_ops # Not strictly needed but good for reference if we personalize later

class OnboardingState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    language: str | None
    interaction_mode: str | None
    table_number: str | None
    step: str # 'ask_lang', 'ask_mode', 'ask_table', 'complete'
    step: str # 'ask_lang', 'ask_mode', 'complete'

def create_onboarding_workflow(llm):
    
    def determine_step(state: OnboardingState):
        """Decide what to ask next."""
        if not state.get("language"):
            return {"step": "ask_lang"}
        elif not state.get("interaction_mode"):
            return {"step": "ask_mode"}
        elif not state.get("table_number"):
             return {"step": "ask_table"}
        else:
            return {"step": "complete"}

    def ask_language(state: OnboardingState):
        """Ask for preferred language."""
        # Check if user already answered in the last message
        msgs = state.get("messages", [])
        if msgs and isinstance(msgs[-1], HumanMessage):
            content = msgs[-1].content.lower()
            
            from storage import db
            # Extract basic user_id from session_id (e.g. "12345_1" -> "12345")
            user_id = state['session_id'].split('_')[0]
            
            selected_lang = None
            response_text = ""
            
            # Simple heuristic or LLM based. Let's use simple keywords for robust speed.
            if "english" in content:
                selected_lang = "English"
                response_text = "Great, English it is."
            elif "hausa" in content:
                selected_lang = "Hausa"
                response_text = "To, za mu yi magana da Hausa."
            elif "yoruba" in content:
                selected_lang = "Yoruba"
                response_text = "O da, a ma sọ Yoruba."
            elif "igbo" in content:
                selected_lang = "Igbo"
                response_text = "Ọ dị mma, anyị ga-asụ Igbo."
            elif "french" in content:
                selected_lang = "French"
                response_text = "D'accord, nous parlerons français."
            
            if selected_lang:
                # Persist to DB
                db.set_user_pref(user_id, language=selected_lang)
                
                # Append Note
                note = "\n\n(Note: You can change your selected language anytime by typing 'reset language'.)"
                if selected_lang == "Hausa": note = "\n\n(Lura: Kuna iya canza yaren da kuka zaɓa kowane lokaci ta hanyar rubuta 'reset language'.)"
                elif selected_lang == "French": note = "\n\n(Note : Vous pouvez changer votre langue sélectionnée à tout moment en tapant 'reset language'.)"
                # Keep other langs default English note or translate if capable, but Requirement said "Note: ..."
                
                return {"language": selected_lang, "messages": [AIMessage(content=response_text + note)]}
            
            # If it's the very first interaction (start)
            if len(msgs) == 1 and not state.get("language"):
                 # Prompt again
                 pass
        
        msg = "Hi, Welcome to Evolution Restaurant! Am Smart-Waiter. Please select your preferred language: English, Hausa, Yoruba, Igbo, or French for us to continue."
        return {"messages": [AIMessage(content=msg)]}

    def ask_mode(state: OnboardingState):
        """Ask for voice or message."""
        msgs = state.get("messages", [])
        if msgs and isinstance(msgs[-1], HumanMessage):
            content = msgs[-1].content.lower()
            if any(k in content for k in ["voice", "murya", "ohùn", "olu", "voix"]):
                # User chose Voice
                # The response will be TTS'd by the API layer, but the text remains the same.
                lang = state.get("language", "English")
                responses = {
                    "English": "Welcome once again! What can I get for you today? or Would you like to see our menu?",
                    "Hausa": "Barka da sake zuwa! Me zan kawo muku yau? Ko kuna so ku ga menu?",
                    "Yoruba": "Ẹ kaabọ lẹẹkansi! Kí ni mo lè mú wá fún yín lónìí? Tabi ṣe ẹ fẹ wo akojọ ounjẹ wa?",
                    "Igbo": "Nnọọ ọzọ! Kedu ihe m ga-wetara gị taa? Ka ị chọrọ ịhụ menu anyị?",
                    "French": "Bienvenue encore une fois ! Que puis-je vous servir aujourd'hui ? Ou souhaitez-vous voir notre menu ?"
                }
                msg = responses.get(lang, responses["English"])
                
                # Persist
                from storage import db
                user_id = state['session_id'].split('_')[0]
                db.set_user_pref(user_id, interaction_mode="voice")
                
                return {"interaction_mode": "voice", "messages": [AIMessage(content=msg)]}
            elif any(k in content for k in ["message", "text", "rubutu", "ifiranṣẹ", "ozi", "texte"]):
                # User chose Message
                lang = state.get("language", "English")
                responses = {
                    "English": "Welcome once again! What can I get for you today? or Would you like to see our menu?",
                    "Hausa": "Barka da sake zuwa! Me zan kawo muku yau? Ko kuna so ku ga menu?",
                    "Yoruba": "Ẹ kaabọ lẹẹkansi! Kí ni mo lè mú wá fún yín lónìí? Tabi ṣe ẹ fẹ wo akojọ ounjẹ wa?",
                    "Igbo": "Nnọọ ọzọ! Kedu ihe m ga-wetara gị taa? Ka ị chọrọ ịhụ menu anyị?",
                    "French": "Bienvenue encore une fois ! Que puis-je vous servir aujourd'hui ? Ou souhaitez-vous voir notre menu ?"
                }
                msg = responses.get(lang, responses["English"])
                
                # Persist
                from storage import db
                user_id = state['session_id'].split('_')[0]
                db.set_user_pref(user_id, interaction_mode="message")
                
                return {"interaction_mode": "message", "messages": [AIMessage(content=msg)]}
        
        # If language is known, we could customize this prompt, but keeping it simple for now.
        lang = state.get("language", "English")
        
        # Multilingual prompt mappings could go here. Defaulting to English for simplicity or LLM translation later.
        msg = "Would you like to continue via Voice or Message?"
        if lang == "Hausa": msg = "Kuna so mu ci gaba da Murya ko Rubutu?"
        elif lang == "Yoruba": msg = "Ṣe o fẹ tẹsiwaju pẹlu Ohùn tabi Ifiranṣẹ?"
        elif lang == "Igbo": msg = "Ị chọrọ iji Olu ka ọ bụ Ozi gaa n'ihu?"
        elif lang == "French": msg = "Souhaitez-vous continuer par Voix ou Message ?"
            
        return {"messages": [AIMessage(content=msg)]}

    def ask_table(state: OnboardingState):
        """Ask for table number (1-15) or None."""
        msgs = state.get("messages", [])
        lang = state.get("language", "English")
        
        # Responses map
        responses = {
            "English": "Great! Finally, could you please tell me your table number (1-15)? If you are not seated, just say 'None'.",
            "Hausa": "Yauwa! A ƙarshe, don Allah faɗa min lambar tebur ɗin ku (1-15)? Idan ba ku zauna ba, sai ku ce 'Babu'.",
            "Yoruba": "O da! Lakotan, jọwọ sọ nọmba tabili rẹ fun mi (1-15)? Ti o ko ba joko, sọ 'Ko si'.",
            "Igbo": "Ọ dị mma! N'ikpeazụ, biko gwa m nọmba tebụl gị (1-15)? Ọ bụrụ na ị nọghị ọdụ, sọ sị 'Ọ dịghị'.",
            "French": "Super ! Enfin, pourriez-vous me dire votre numéro de table (1-15) ? Si vous n'êtes pas assis, dites simplement 'Aucun'."
        }
        
        prompt_msg = responses.get(lang, responses["English"])
        
        if msgs and isinstance(msgs[-1], HumanMessage):
            content = msgs[-1].content.lower()
            
            # Check for "none" variations
            if any(k in content for k in ["none", "babu", "ko si", "ọ dịghị", "aucun", "no", "not seated"]):
                # Success
                final_msg = "Thank you! You are all set. What can I get for you today? or Would you like to see our menu?" # Simplified final msg, re-used in welcome
                return {"table_number": "None", "messages": [AIMessage(content=final_msg)]}
            
            # Extract number
            import re
            numbers = re.findall(r'\d+', content)
            if numbers:
                num = int(numbers[0])
                if 1 <= num <= 15:
                    success_responses = {
                        "English": f"Table {num} noted. Thank you! What can I get for you today? or Would you like to see our menu?",
                        "Hausa": f"An lura da tebur {num}. Na gode! Me zan kawo muku yau? Ko kuna so ku ga menu?",
                        "Yoruba": f"A ti kọ tabili {num}. Ẹ ṣeun! Kí ni mo lè mú wá fún yín lónìí? Tabi ṣe ẹ fẹ wo akojọ ounjẹ wa?",
                        "Igbo": f"Edebere tebụl {num}. Daalụ! Kedu ihe m ga-wetara gị taa? Ka ị chọrọ ịhụ menu anyị?",
                        "French": f"Table {num} notée. Merci ! Que puis-je vous servir aujourd'hui ? Ou souhaitez-vous voir notre menu ?"
                    }
                    final_msg = success_responses.get(lang, success_responses["English"])
                    return {"table_number": str(num), "messages": [AIMessage(content=final_msg)]}
                else:
                    # Invalid number
                    err_responses = {
                        "English": "Please enter a valid table number between 1 and 15.",
                         "Hausa": "Don Allah shigar da lambar tebur mai inganci tsakanin 1 da 15.",
                         "French": "Veuillez entrer un numéro de table valide entre 1 et 15."
                    }
                    err_msg = err_responses.get(lang, err_responses["English"])
                    return {"messages": [AIMessage(content=err_msg)]}
            
            # If explicit input but not understood, just repeat prompt? or assume it's the prompt turn.
            
        return {"messages": [AIMessage(content=prompt_msg)]}

    workflow = StateGraph(OnboardingState)
    
    workflow.add_node("decider", determine_step)
    workflow.add_node("ask_lang", ask_language)
    workflow.add_node("ask_mode", ask_mode)
    workflow.add_node("ask_table", ask_table)
    
    workflow.set_entry_point("decider")
    
    workflow.add_conditional_edges(
        "decider",
        lambda x: x['step'],
        {
            "ask_lang": "ask_lang",
            "ask_mode": "ask_mode",
            "ask_table": "ask_table",
            "complete": END
        }
    )
    
    # After asking, we end this turn and wait for user input (which re-triggers the agent)
    # But wait, this is a subgraph. We need it to return to the main agent to wait for input.
    # The main agent loop handles "execution" -> "user input".
    # So here we just output the message.
    
    workflow.add_conditional_edges(
        "ask_lang",
        lambda x: "continue" if x.get("language") else "stop",
        {
            "continue": "decider",
            "stop": END
        }
    )
    workflow.add_conditional_edges(
        "ask_mode",
        lambda x: "continue" if x.get("interaction_mode") else "stop",
         {
            "continue": "decider",
            "stop": END
        }
    )
    workflow.add_edge("ask_table", END)
    
    return workflow.compile()
