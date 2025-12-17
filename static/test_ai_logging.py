"""
Òåñòîâûé ñêðèïò äëÿ ïðîâåðêè AI ëîãèðîâàíèÿ è ðàáîòû ïðîâåðêè
Çàïóñòèòå ýòîò ôàéë îòäåëüíî äëÿ äèàãíîñòèêè ïðîáëåì
"""

import os
import sys
import json
from datetime import datetime

# Äîáàâëÿåì ïóòü ê ïðîåêòó
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ai_config():
    """Òåñò çàãðóçêè êîíôèãóðàöèè AI"""
    print("=" * 60)
    print("ÒÅÑÒ 1: Ïðîâåðêà êîíôèãóðàöèè AI")
    print("=" * 60)
    
    try:
        from ai_config import AIConfig
        
        print(f"? AI ìîäóëü çàãðóæåí óñïåøíî")
        print(f"   API Key íàñòðîåí: {AIConfig.GEMINI_API_KEY != 'YOUR_API_KEY_HERE'}")
        print(f"   Ìîäåëü: {AIConfig.GEMINI_MODEL}")
        print(f"   AI ïðîâåðêà âêëþ÷åíà: {AIConfig.AI_CHECKING_ENABLED}")
        print(f"   Ëîãèðîâàíèå âêëþ÷åíî: {AIConfig.LOG_AI_REQUESTS}")
        print(f"   Ôàéë ëîãîâ: {AIConfig.AI_LOG_FILE}")
        
        # Ïðîâåðÿåì äèðåêòîðèþ äëÿ ëîãîâ
        log_dir = os.path.dirname(AIConfig.AI_LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"? Ñîçäàíà äèðåêòîðèÿ äëÿ ëîãîâ: {log_dir}")
        
        return True
        
    except Exception as e:
        print(f"? Îøèáêà çàãðóçêè êîíôèãóðàöèè: {e}")
        return False


def test_ai_checker():
    """Òåñò èíèöèàëèçàöèè AI checker"""
    print("\n" + "=" * 60)
    print("ÒÅÑÒ 2: Èíèöèàëèçàöèÿ AI Checker")
    print("=" * 60)
    
    try:
        from ai_checker_0 import AIAnswerChecker
        from ai_config import AIConfig
        
        checker = AIAnswerChecker(provider="gemini", api_key=AIConfig.GEMINI_API_KEY)
        print(f"? AI Checker ñîçäàí óñïåøíî")
        print(f"   Ïðîâàéäåð: {checker.provider}")
        print(f"   API Key ïðèñóòñòâóåò: {bool(checker.api_key)}")
        
        return checker
        
    except Exception as e:
        print(f"? Îøèáêà ñîçäàíèÿ AI Checker: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_ai_check(checker):
    """Òåñò ïðîâåðêè îòâåòà ÷åðåç AI"""
    print("\n" + "=" * 60)
    print("ÒÅÑÒ 3: Ïðîâåðêà îòâåòà ÷åðåç AI")
    print("=" * 60)
    
    if not checker:
        print("? AI Checker íå èíèöèàëèçèðîâàí")
        return False
    
    test_cases = [
        {
            "student_answer": "Àñòàíà",
            "correct_variants": ["Àñòàíà", "àñòàíà"],
            "context": "Ñòîëèöà Êàçàõñòàíà"
        },
        {
            "student_answer": "ñòîëèöà Êàçàõñòàíà",
            "correct_variants": ["Àñòàíà"],
            "context": "Ãëàâíûé ãîðîä ñòðàíû"
        },
        {
            "student_answer": "Êàðàãàíäà",
            "correct_variants": ["Àñòàíà"],
            "context": "Ñòîëèöà Êàçàõñòàíà"
        }
    ]
    
    from ai_config import AIConfig
    from dataclasses import asdict
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nÒåñò {i}:")
        print(f"  Îòâåò ñòóäåíòà: '{test['student_answer']}'")
        print(f"  Ïðàâèëüíûå îòâåòû: {test['correct_variants']}")
        
        try:
            result = checker.check_answer(
                student_answer=test['student_answer'],
                correct_variants=test['correct_variants'],
                question_context=test['context'],
                system_prompt=AIConfig.SYSTEM_PROMPT,
                model_name=AIConfig.GEMINI_MODEL
            )
            
            result_dict = asdict(result)
            
            print(f"  ? Ðåçóëüòàò: {'ÂÅÐÍÎ' if result.is_correct else 'ÍÅÂÅÐÍÎ'}")
            print(f"  Óâåðåííîñòü: {result.confidence * 100:.1f}%")
            print(f"  Îáúÿñíåíèå: {result.explanation}")
            print(f"  Ïðîâàéäåð: {result.ai_provider}")
            
            # Òåñò ëîãèðîâàíèÿ
            if AIConfig.LOG_AI_REQUESTS:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "test_case": i,
                    "student_answer": test['student_answer'],
                    "correct_variants": test['correct_variants'],
                    "result": result_dict,
                    "success": True
                }
                
                log_file = AIConfig.AI_LOG_FILE
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
                print(f"  ?? Ëîã çàïèñàí â {log_file}")
            
        except Exception as e:
            print(f"  ? Îøèáêà ïðîâåðêè: {e}")
            import traceback
            traceback.print_exc()
    
    return True


def check_log_file():
    """Ïðîâåðêà ôàéëà ëîãîâ"""
    print("\n" + "=" * 60)
    print("ÒÅÑÒ 4: Ïðîâåðêà ôàéëà ëîãîâ")
    print("=" * 60)
    
    try:
        from ai_config import AIConfig
        
        log_file = AIConfig.AI_LOG_FILE
        
        if not os.path.exists(log_file):
            print(f"??  Ôàéë ëîãîâ íå ñóùåñòâóåò: {log_file}")
            return False
        
        print(f"? Ôàéë ëîãîâ íàéäåí: {log_file}")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"   Êîëè÷åñòâî çàïèñåé: {len(lines)}")
        
        if lines:
            print(f"\n   Ïîñëåäíèå 3 çàïèñè:")
            for line in lines[-3:]:
                try:
                    entry = json.loads(line)
                    print(f"   - {entry.get('timestamp', 'N/A')}: {entry.get('student_answer', 'N/A')}")
                except:
                    print(f"   - [Íåêîððåêòíàÿ çàïèñü]")
        
        return True
        
    except Exception as e:
        print(f"? Îøèáêà ïðîâåðêè ëîãîâ: {e}")
        return False


def main():
    """Ãëàâíàÿ ôóíêöèÿ òåñòèðîâàíèÿ"""
    print("\n" + "-" * 60)
    print("-" + " " * 58 + "-")
    print("-" + "  ÒÅÑÒÈÐÎÂÀÍÈÅ AI ÏÐÎÂÅÐÊÈ È ËÎÃÈÐÎÂÀÍÈß".center(58) + "-")
    print("-" + " " * 58 + "-")
    print("-" * 60 + "\n")
    
    # Òåñò 1: Êîíôèãóðàöèÿ
    if not test_ai_config():
        print("\n? Òåñòû îñòàíîâëåíû èç-çà îøèáêè êîíôèãóðàöèè")
        return
    
    # Òåñò 2: Èíèöèàëèçàöèÿ checker
    checker = test_ai_checker()
    if not checker:
        print("\n? Òåñòû îñòàíîâëåíû èç-çà îøèáêè èíèöèàëèçàöèè")
        return
    
    # Òåñò 3: Ïðîâåðêà îòâåòîâ
    test_ai_check(checker)
    
    # Òåñò 4: Ïðîâåðêà ëîãîâ
    check_log_file()
    
    print("\n" + "=" * 60)
    print("ÒÅÑÒÈÐÎÂÀÍÈÅ ÇÀÂÅÐØÅÍÎ")
    print("=" * 60)
    print("\nÐåêîìåíäàöèè:")
    print("1. Ïðîâåðüòå, ÷òî GEMINI_API_KEY óñòàíîâëåí êîððåêòíî")
    print("2. Óáåäèòåñü, ÷òî äèðåêòîðèÿ 'logs/' ñóùåñòâóåò è äîñòóïíà äëÿ çàïèñè")
    print("3. Ïðîâåðüòå ëîãè â ôàéëå äëÿ îòëàäêè ïðîáëåì")
    print("4. Åñëè AI íå ðàáîòàåò, ïðîâåðüòå êâîòû API â Google Cloud Console")


if __name__ == "__main__":
    main()