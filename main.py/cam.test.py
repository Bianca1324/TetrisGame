import cv2

# Deschide camera implicită (0 este de obicei camera laptopului)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Nu s-a putut accesa camera.")
else:
    print("Camera pornită. Apasă 'q' pentru a închide.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Nu s-a putut citi cadrul de la cameră.")
        break

    # Afișează imaginea
    cv2.imshow('Test Camera', frame)

    # Închide cu 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Eliberează camera și închide ferestrele
cap.release()
cv2.destroyAllWindows()

