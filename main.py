import cv2
import os
import pickle
import face_recognition
import numpy as np
import cvzone
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from datetime import datetime

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
  "databaseURL": "https://attendance-system-2742c-default-rtdb.firebaseio.com/",
  "storageBucket": "attendance-system-2742c.appspot.com"
})

bucket = storage.bucket()

# initializing webcam and reading background image
capture = cv2.VideoCapture(0); # 0 - built-in webcam, 1 - external webcam
# resize to place the webcam in our background image
capture.set(3, 640) # 3 - width
capture.set(4, 480) # 4 - height
backgroundImg = cv2.imread('Resources/Background.png')

folderPathModes = 'Resources/Modes'
# the list of file names in folderPathModes is retrieved and stored into listPathModes
listPathModes = os.listdir(folderPathModes)
# images inside 'Resources/Modes' will be stored in this list afterwards
imgListModes = []

# the FOR loop iterates over each path in listPathModes and APPENDS them to imgListModes
# imgListModes is a LIST that stores the full path of each image
for path in listPathModes: # listPathModes contains "1.png", "2.png" and so on
  # each item stored in the list would look something like this: Resources/Modes/1.png
  imgListModes.append(cv2.imread(os.path.join(folderPathModes, path)))

# open the file in READ MODE (binary)
encodingsFile = open("EncodingsFile.p", "rb")
# "deserialize" the contents in the file
encodingsListWithIds = pickle.load(encodingsFile)
encodingsFile.close()

encodingsListKnown, studentIds = encodingsListWithIds
print(studentIds)

modeType = 0
counter = 0
id = -1

while True:
  success, image = capture.read()

  # overlay the webcam feed over our image to display the 2 components together
  backgroundImg[162:162 + 480, 55:55 + 640] = image
  # overlay the FIRST element within imgListModes on top of the background
  backgroundImg[44:44 + 633, 808:808 + 414] = imgListModes[modeType]

  # resize image to 1/4 of its original size because encoding large images requires a lot of computational power
  smallImage = cv2.resize(image, (0, 0), None, 0.25, 0.25)
  smallImage = cv2.cvtColor(smallImage, cv2.COLOR_BGR2RGB)

  # LOCATING the face in the current frame
  faceCurrentFrame = face_recognition.face_locations(smallImage)
  # converting facial features in the current frame into encodings
  encodeCurrentFrame = face_recognition.face_encodings(smallImage, faceCurrentFrame)

  if faceCurrentFrame:
    for encodeFace, faceLocation in zip(encodeCurrentFrame, faceCurrentFrame):
      matches = face_recognition.compare_faces(encodingsListKnown, encodeFace)
      # face_distance measures how similar your face is to a certain image/face
      # the lower the score, the more similar it is
      faceDistance = face_recognition.face_distance(encodingsListKnown, encodeFace)
      print("Matches", matches)
      print("Face Distance", faceDistance)

      # for even cleaner results, you can calculate the matchIndex
      matchIndex = np.argmin(faceDistance)
      print("Match Index", matchIndex)

      # display the matching student id instead of [False, False, True, False]
      if matches[matchIndex]:
        print("Registered Student Detected")
        print(studentIds[matchIndex])

        # creating four points to map as the "corners" of your face
        y1, x2, x1, y2 = faceLocation
        # resizing it 4x back to the original size of the webcam feed
        y1, x2, x1, y2 = y1*4, x2*4, x1*4, y2*4
        # adjusting where the box's coordinates are
        bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
        # draw the rectangle onto the backgroundImg image, rt=0 means you are not outlining the box
        backgroundImg = cvzone.cornerRect(backgroundImg, bbox, rt=0)

        # saves the current id as the match to the face in the current frame
        id = studentIds[matchIndex]

        if counter == 0:
          counter = 1
          modeType = 1 # change this to 1 so the graphics is updated at the side of the pagez

    if counter != 0:
      if counter == 1:
        studentInfo = db.reference(f'Students/{id}').get()
        print(studentInfo)

        # retrieving student's image from the storage
        blob = bucket.get_blob(f'Images/{id}.png')
        array = np.frombuffer(blob.download_as_string(), np.uint8)
        studentImg = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)

        # Update attendance record and data

        # last attendance taken
        datetimeObject = datetime.strptime(studentInfo['last_attendance_taken'], "%Y-%m-%d %H:%M:%S")
        timeInSecsElapsed = (datetime.now() - datetimeObject).total_seconds()

        # only update if the time elapsed has exceeeded a certain threshold
        if timeInSecsElapsed > 30:
          ref = db.reference(f'Students/{id}')
          studentInfo['total_attendance'] += 1

          ref.child('total_attendance').set(studentInfo['total_attendance'])
          ref.child('last_attendance_taken').set(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        else:
          modeType = 3 # already marked
          counter = 0
          backgroundImg[44:44 + 633, 808:808 + 414] = imgListModes[modeType]
      
      if modeType != 3:
        if 10 < counter < 20:
          modeType = 2
        
        backgroundImg[44:44 + 633, 808:808 + 414] = imgListModes[modeType]

        if counter < 10:
          # all while execute while modeType = 1

          cv2.putText(backgroundImg, str(studentInfo['total_attendance']), (861, 125),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
          cv2.putText(backgroundImg, str(studentInfo['major']), (1006, 550),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
          cv2.putText(backgroundImg, str(id), (1006, 493),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
          cv2.putText(backgroundImg, str(studentInfo['grades']), (910, 625),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
          cv2.putText(backgroundImg, str(studentInfo['year']), (1025, 625),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
          cv2.putText(backgroundImg, str(studentInfo['starting_year']), (1125, 625),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 1)

          # to center the name
          (width, height), _ = cv2.getTextSize(studentInfo['name'], cv2.FONT_HERSHEY_SIMPLEX, 1, 1)

          # using double to get rid of trailing float numbers
          center_offset = (414 - width) // 2
          cv2.putText(backgroundImg, str(studentInfo['name']), (808 + center_offset, 445),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (50, 50, 50), 1)
          
          backgroundImg[175:175 + 216, 909:909 + 216] = studentImg

        counter += 1

        if counter > 20:
          counter = 0
          modeType = 0
          studentInfo = []
          studentImg = []
          backgroundImg[44:44 + 633, 808:808 + 414] = imgListModes[modeType]
  # resets the sytem if no faces are detected
  else:
    modeType = 0
    counter = 0

  # showing a window for your background image
  cv2.imshow("Attendance System", backgroundImg)
  cv2.waitKey(1)