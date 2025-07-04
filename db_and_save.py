import os
import cv2
import re
import mysql.connector
import unicodedata
import sys


def ensure_utf8_environment():
    """
    Ensure the environment is set up for UTF-8
    """
    # Set environment variables for UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # For Windows, try to set console to UTF-8
    if sys.platform.startswith('win'):
        try:
            os.system('chcp 65001 >nul 2>&1')
        except:
            pass


def sanitize_filename_ascii_safe(filename):
    """
    Create ASCII-safe filename while preserving readability
    """
    # First, try to transliterate Unicode to ASCII
    try:
        # Remove diacritics and convert to closest ASCII equivalent
        ascii_filename = unicodedata.normalize('NFKD', filename)
        ascii_filename = ''.join(c for c in ascii_filename if not unicodedata.combining(c))
        
        # If still contains non-ASCII, use a different approach
        if not ascii_filename.isascii():
            # Replace common Hindi/Devanagari with transliteration
            transliteration_map = {
                'रायपुर': 'raipur',
                'सामान्य': 'samanya', 
                'दिल्ली': 'delhi',
                'मुंबई': 'mumbai',
                'कोलकाता': 'kolkata',
                'चेन्नई': 'chennai',
                'बैंगलोर': 'bangalore',
                'हैदराबाद': 'hyderabad',
                'पुणे': 'pune',
                'अहमदाबाद': 'ahmedabad',
                'जयपुर': 'jaipur',
                'लखनऊ': 'lucknow',
                'कानपुर': 'kanpur',
                'नागपुर': 'nagpur',
                'इंदौर': 'indore',
                'भोपाल': 'bhopal',
                'पटना': 'patna',
                'गुवाहाटी': 'guwahati',
                'चंडीगढ़': 'chandigarh',
                'नज़ीबाबाद': 'najibabad',
                'चकराता': 'chakrata',
                'विकासनगर': 'vikasnagar',
                'सहसपुर': 'sahaspur',
                'धर्मपुर': 'dharampur',
            }
            
            # Apply transliterations
            for hindi, english in transliteration_map.items():
                ascii_filename = ascii_filename.replace(hindi, english)
            
            # If still not ASCII, create a hash-based name
            if not ascii_filename.isascii():
                import hashlib
                hash_part = hashlib.md5(filename.encode('utf-8')).hexdigest()[:8]
                ascii_filename = f"entry_{hash_part}"
        
        # Clean up the filename
        ascii_filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', ascii_filename)
        ascii_filename = re.sub(r'_+', '_', ascii_filename)
        ascii_filename = ascii_filename.strip('_')
        
        return ascii_filename if ascii_filename else 'entry'
        
    except Exception as e:
        print(f"[WARNING] Filename sanitization failed: {e}")
        return 'entry'


def save_entry_to_db_and_image(result, sequence, sequenceOCR, vidhansabha, image, db_config):
    """
    Save the OCR result to MySQL DB and image to disk, with proper encoding handling.
    """
    
    # Ensure UTF-8 environment
    ensure_utf8_environment()


    # //Uncomment this if you want to save the image
    # # Create ASCII-safe filename
    # safe_vidhansabha = sanitize_filename_ascii_safe(vidhansabha)
    
    # # Create image filename and path with ASCII-safe name
    # image_filename = f"{safe_vidhansabha}_{sequence}.jpg"
    # image_path = os.path.join("output", "images",f"{safe_vidhansabha}", image_filename)

    # # Ensure the output directory exists
    # os.makedirs(os.path.dirname(image_path), exist_ok=True)

    # # # Save image
    # try:
    #     # Use ASCII-safe path for saving
    #     success = cv2.imwrite(image_path, image)
    #     if not success:
    #         print(f"[ERROR] Failed to save image: {image_filename}")
    # except Exception as e:
    #     print(f"[ERROR] Failed to save image: {e}")

    # Save to MySQL with proper encoding
    try:
        # Connect with explicit encoding settings
        conn = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            charset="utf8mb4",
            use_unicode=True,
            autocommit=False
        )
        
        cursor = conn.cursor(buffered=True)
        
        # Force UTF-8 settings
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute("SET CHARACTER SET utf8mb4;")
        cursor.execute("SET character_set_connection=utf8mb4;")
        cursor.execute("SET character_set_results=utf8mb4;")
        cursor.execute("SET character_set_client=utf8mb4;")

        # Create table if not exists with explicit UTF-8 settings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS voter_entries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sequence INT ,
            sequenceOCR VARCHAR(20),
            voterId VARCHAR(100),
            name TEXT,
            relation TEXT,
            relationName TEXT,
            houseNumber TEXT,
            age VARCHAR(10),
            gender VARCHAR(20),
            fileName TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Ensure all data is properly encoded as UTF-8 strings
        def ensure_utf8_string(value):
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode('utf-8', errors='replace')
            return str(value)

        # Prepare data with explicit UTF-8 encoding
        voter_data = (
            sequence,
            sequenceOCR,
            ensure_utf8_string(result.get("voterId", "")),
            ensure_utf8_string(result.get("name", "")),
            ensure_utf8_string(result.get("relation", "")),
            ensure_utf8_string(result.get("relationName", "")),
            ensure_utf8_string(result.get("houseNumber", "")),
            ensure_utf8_string(result.get("Age", "")),
            ensure_utf8_string(result.get("gender", "")),
            ensure_utf8_string(vidhansabha),
        )

        # Insert or update entry
        insert_query = """
        INSERT INTO voter_entries (
            sequence,sequenceOCR, voterId, name, relation, relationName, houseNumber, age, gender, fileName
        ) VALUES (%s, %s,  %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            sequence=VALUES(sequence),
            sequenceOCR=VALUES(sequenceOCR),
            voterId=VALUES(voterId),
            name=VALUES(name),
            relation=VALUES(relation),
            relationName=VALUES(relationName),
            houseNumber=VALUES(houseNumber),
            age=VALUES(age),
            gender=VALUES(gender)
        """
        
        cursor.execute(insert_query, voter_data)
        conn.commit()
        
        
        # Verify the insert by reading it back
        cursor.execute("SELECT name, relationName, fileName FROM voter_entries WHERE sequence = %s", (sequence,))
        result_row = cursor.fetchone()
        

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"[MYSQL ERROR] {err}")
    except Exception as e:
        print(f"[ERROR] Unexpected database error: {e}")


def debug_encoding_info():
    """
    Print encoding information for debugging
    """
    print("=== ENCODING DEBUG INFO ===")
    print(f"System encoding: {sys.getdefaultencoding()}")
    print(f"File system encoding: {sys.getfilesystemencoding()}")
    print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'Not set')}")
    
    # Test Hindi text
    test_text = "रायपुर"
    print(f"Test text: {test_text}")
    print(f"Test text bytes: {test_text.encode('utf-8')}")
    print(f"Test text repr: {repr(test_text)}")
    print("=== END DEBUG INFO ===")


def fix_database_encoding(db_config):
    """
    Fix database encoding issues
    """
    try:
        conn = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            charset="utf8mb4",
            use_unicode=True
        )
        
        cursor = conn.cursor()
        
        # Drop and recreate table with proper encoding
        cursor.execute("DROP TABLE IF EXISTS voter_entries_backup;")
        cursor.execute("CREATE TABLE voter_entries_backup AS SELECT * FROM voter_entries;")
        cursor.execute("DROP TABLE voter_entries;")
        
        # Create new table with proper charset
        cursor.execute("""
        CREATE TABLE voter_entries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sequence INT,
            sequenceOCR VARCHAR(10),
            voterId VARCHAR(100),
            name TEXT,
            relation TEXT,
            relationName TEXT,
            houseNumber TEXT,
            age VARCHAR(10),
            gender VARCHAR(20),
            fileName TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
                
    except mysql.connector.Error as err:
        print(f"[MYSQL ERROR] Failed to fix encoding: {err}")


# Example usage and testing
if __name__ == "__main__":
    # Print debug info
    debug_encoding_info()
    
    # Example database config
    db_config = {
        "host": "localhost",
        "user": "your_username", 
        "password": "your_password",
        "database": "your_database"
    }
    
    # Test filename sanitization
    test_vidhansabha = "19_रायपुर_सामान्य_111"
    print(f"Original: {test_vidhansabha}")
    print(f"Sanitized: {sanitize_filename_ascii_safe(test_vidhansabha)}")
    
    # Uncomment to fix database
    # fix_database_encoding(db_config)