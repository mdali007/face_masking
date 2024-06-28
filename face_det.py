import cv2 as cv
import dlib

# Load the pre-trained face detection model from dlib
detector = dlib.get_frontal_face_detector()

# Read the image
img = cv.imread('img/insta3.jpeg', cv.IMREAD_COLOR)
if img is None:
    print('Error: Image not found or unable to read.')
    exit()

# Convert the image to RGB (dlib requires RGB format)
img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
print(f"Image format after conversion: {img_rgb.dtype}")  # Check data type

# Detect faces using dlib on the RGB image
faces_rects = detector(img_rgb, 0)

# Draw rectangles around detected faces on the original BGR image
for rect in faces_rects:
    cv.rectangle(img, (rect.left(), rect.top()), (rect.right(), rect.bottom()), (0, 255, 0), 2)

# Display the output
cv.imshow('Detected Faces', img)
cv.waitKey(0)
cv.destroyAllWindows()
