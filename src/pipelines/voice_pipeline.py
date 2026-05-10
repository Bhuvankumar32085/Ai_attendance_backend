from resemblyzer import VoiceEncoder, preprocess_wav # ye embadding banata h
import numpy as np
import io
import librosa # es ka kaam hota h audio gile ko load karna noice nikal na etc

# Load once (IMPORTANT)
encoder = VoiceEncoder()

def get_voice_embedding(audio_bytes): # audio_bytes = Audio file ka raw data (binary form)
    try:
        # load audio from bytes
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000) #librosa.load = Audio file → numbers (waveform) me convert
        # sr(sample rate) matlab 1 second me kitne audio samples
        # BytesIO ye help karti h audio file ko librosa me load hone keliye
        
        # preprocess
        wav = preprocess_wav(audio) #Audio ko clean aur model-ready banata hai kyo ki audio me noise ho sakte h un sab ko thik karta h ,beech ka khaali part hata deta hai,sab audio same loudness pe laata hai

        # embedding (correct method name)
        embedding = encoder.embed_utterance(wav)

        return embedding.tolist()

    except Exception as e:
        print("Error in voice embedding:", e)
        return None
    
def identify_specker(new_embedding,candidates_dict,threshold=0.60):
    
    if new_embedding is None:
            return {
            "success": False,
            "error": "Voice embedding generation failed"
        }

    if not candidates_dict:
        return {
            "success": False,
            "error": "No registered voice embeddings found"
        }

    
    best_sid=True
    best_score=-1.0
    
    for sid , stored_embedding in candidates_dict.items():
        if stored_embedding is not None:
            similarity=np.dot(new_embedding,stored_embedding)
            if similarity>best_score:
                best_score=similarity
                best_sid=sid
                
    print("BEST SID:", best_sid)
    print("BEST SCORE:", best_score)
    
    if best_score < threshold:
        return {
            "success": False,
            "error": "Voice matched but confidence too low",
            "best_sid": best_sid,
            "score": float(best_score)
        }

    
    if best_score>=threshold:
        return best_sid ,best_score
    
    return None ,best_score
            

def process_bulk_audio(audio_bytes,candidates_dict,threshold=0.65):
    try:
        audio,sr=librosa.load(io.BytesIO(audio_bytes),sr=16000)# yaha bhot badi audio aagi jisme ho sakta h bhoth sare user ho
        
        segments = librosa.effects.split(audio,top_db=30)# es se sb user ki voice hum segment me lele ge top_db agar jada bada rakh diya to bs un user ki audio segment me aahi jo bhoth joor se bool rahe h es le 30 ek best value h
        # librosa.effects.split deta h [(start1, end1), (start2, end2), ...]
        identified_result={}
        
        for start,end in segments:
            if (end-start) < sr*0.5:
                # end-start dega audio len or sr(16000)*0.5=8000 matlab 0.5 sec to hum yaha check karre ki agar len segment ki 0.5 sec se choti to
                # 1 sec 16000 semple 0.5 sec to 8000 semple agar video ki length 8000 semple se chota h to
                continue # continue matlab skip
            segment_audio=audio[start:end]
            wav=preprocess_wav(segment_audio)
            
            embedding=encoder.embed_utterance(wav)
            
            sid , score = identify_specker(embedding,candidates_dict,threshold)
            
            if sid:
                if sid not in identified_result or score > identified_result[sid]:
                    identified_result[sid]=score
                    
        return identified_result              
                
    except Exception as error:
        print(error)
        return None
    
    
