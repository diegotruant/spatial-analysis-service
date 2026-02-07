"""
Script per verificare se i file FIT/TCX contengono dati RR
Eseguire su un campione di file per capire la disponibilità
"""

def check_fit_for_rr(file_path: str):
    """
    Verifica se un file FIT contiene dati RR.
    Richiede: pip install fitparse
    """
    try:
        from fitparse import FitFile
        
        fitfile = FitFile(file_path)
        has_rr = False
        rr_count = 0
        
        for record in fitfile.get_messages('record'):
            for field in record:
                if 'heart_rate' in field.name.lower() or 'rr' in field.name.lower():
                    print(f"Found field: {field.name} = {field.value}")
                    if 'rr' in field.name.lower():
                        has_rr = True
                        rr_count += 1
        
        return has_rr, rr_count
    except ImportError:
        print("⚠️ fitparse not installed. Run: pip install fitparse")
        return False, 0
    except Exception as e:
        print(f"Error reading FIT file: {e}")
        return False, 0


def check_tcx_for_rr(file_path: str):
    """
    Verifica se un file TCX contiene dati RR
    """
    try:
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Namespace TCX
        ns = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
        
        has_rr = False
        rr_count = 0
        
        # Cerca elementi RR
        for trackpoint in root.findall('.//tcx:Trackpoint', ns):
            extensions = trackpoint.find('tcx:Extensions', ns)
            if extensions is not None:
                # Cerca RRIntervals
                rr_elem = extensions.find('.//*[local-name()="RRIntervals"]')
                if rr_elem is not None:
                    has_rr = True
                    rr_count += len(list(rr_elem))
        
        return has_rr, rr_count
    except Exception as e:
        print(f"Error reading TCX file: {e}")
        return False, 0


print("=" * 70)
print("RR DATA AVAILABILITY CHECKER")
print("=" * 70)
print("\nQuesto script verifica se i tuoi file workout contengono dati RR.")
print("I dati RR sono necessari per DFA alpha 1 analysis.\n")

print("📋 ISTRUZIONI:")
print("1. Carica un file FIT o TCX recente da una tua attività")
print("2. Usa una fascia cardio che supporta RR (Polar H10, Garmin HRM-Pro, ecc.)")
print("3. Esegui questo script sul file\n")

print("💡 ESEMPIO D'USO:")
print("   python check_rr_availability.py")
print("   # Poi modifica lo script sotto per puntare al tuo file\n")

# ========== CONFIGURA QUI IL TUO FILE ==========
# Decommentare e modificare con il percorso del tuo file
# TEST_FILE = "C:/path/to/your/activity.fit"
# TEST_FILE_TYPE = "fit"  # oppure "tcx"

TEST_FILE = None
TEST_FILE_TYPE = None
# ===============================================

if TEST_FILE and TEST_FILE_TYPE:
    print(f"🔍 Checking file: {TEST_FILE}\n")
    
    if TEST_FILE_TYPE.lower() == "fit":
        has_rr, count = check_fit_for_rr(TEST_FILE)
    elif TEST_FILE_TYPE.lower() == "tcx":
        has_rr, count = check_tcx_for_rr(TEST_FILE)
    else:
        print("❌ Tipo file non supportato. Usa 'fit' o 'tcx'")
        has_rr, count = False, 0
    
    print("\n" + "=" * 70)
    print("RISULTATI")
    print("=" * 70)
    
    if has_rr:
        print(f"✅ DATI RR TROVATI! ({count} valori)")
        print("\n🎉 Il tuo dispositivo supporta RR intervals!")
        print("   Posso implementare DFA alpha 1 analysis.")
    else:
        print("❌ NESSUN DATO RR TROVATO")
        print("\n⚠️ Possibili cause:")
        print("   1. La fascia cardio non trasmette RR")
        print("   2. L'app non registra RR anche se trasmessi")
        print("   3. Il formato file non include RR")
        print("\n💡 Soluzioni:")
        print("   - Usa Polar H10, Garmin HRM-Pro, o Wahoo TICKR X")
        print("   - Verifica impostazioni app (abilitare RR recording)")
        print("   - Prova con un'attività più recente")
else:
    print("⚠️ Configura TEST_FILE e TEST_FILE_TYPE nello script prima di eseguire")
    print("\nEsempio:")
    print('TEST_FILE = "C:/Users/Diego/workout.fit"')
    print('TEST_FILE_TYPE = "fit"')

print("\n" + "=" * 70)
print("📚 INFORMAZIONI AGGIUNTIVE")
print("=" * 70)
print("\nDFA alpha 1 richiede:")
print("  • Stream continuo di intervalli RR (ms)")
print("  • Minimo 2-3 minuti di dati per calcolo affidabile")
print("  • Frequenza campionamento: ~1 Hz")
print("\nBenefici DFA alpha 1:")
print("  • Identifica VT1 senza test lattato")
print("  • Monitoraggio real-time durante allenamento")
print("  • Guida intensità zona 2 con precisione")
