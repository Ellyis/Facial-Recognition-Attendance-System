import cv2
import face_recognition
import pickle
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
  "databaseURL": "https://attendance-system-2742c-default-rtdb.firebaseio.com/",
  "storageBucket": "attendance-system-2742c.appspot.com"
})

# importing students' images from 'Images' by using the same logic as earlier
folderPathImages = 'Images'
listPathImages = os.listdir(folderPathImages)
imgListImages = []

# extracting student ids from each image
studentIds = []
print(listPathImages)

for path in listPathImages:
  imgListImages.append(cv2.imread(os.path.join(folderPathImages, path)))
  # splitext splits the file path into 2 parts, the file name, and the file type
  studentIds.append(os.path.splitext(path)[0]) # removes file extension (.png)

  # store the images in firebase storage
  fileName = f'{folderPathImages}/{path}'
  # retrieve a reference to your established cloud storage
  bucket = storage.bucket()
  # reference to a specific object is created
  blob = bucket.blob(fileName)
  # the file with the fileName is uploaded to the reference "blob" created in your cloud storage
  blob.upload_from_filename(fileName)

def generateEncodings(images):
  encodingsList = []

  for img in images:
    # change the color format to RGB as it is the color format that is compatible with FACE-RECOGNITION
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # there might be other faces in the images, so you might have to find the encodings for all the faces in the images
    # here, it is assumed that there is only 1 face in each image
    encode = face_recognition.face_encodings(img)[0] # extract only 1 set of encodings for 1 face
    encodingsList.append(encode)
  
  return encodingsList

encodingsListKnown = generateEncodings(imgListImages)
encodingsListWithIds = [encodingsListKnown, studentIds]

# opening a new file called 'EncodingsFile.p' in WRITE MODE (binary)
# .p is a pickle data file which is used to keep serialized data
encodingFile = open("EncodingsFile.p", "wb")
# dump is a function used to serialize objects, flattening the data into a stream of bytes for easier transmission over the network
pickle.dump(encodingsListWithIds, encodingFile)

encodingFile.close()