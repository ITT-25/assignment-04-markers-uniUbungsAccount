import math
import time
import random
from collections import deque
from pathlib import Path

import cv2
import cv2.aruco as aruco
import pyglet

from helpers import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    loadImg,
    convertCvFrameToPyglet,
    warpCameraImageToWholeScreen,
    findHighestVisibleFingertipCandidate
)

BIRD_RADIUS_PIXELS = 16
PIPE_HORIZONTAL_SPEED = 155
PIPE_GAP_HEIGHT_PIXELS = 200
SECONDS_BETWEEN_PIPE_SPAWNS = 2.8
PIPE_MIN_Y_POS = 100
PIPE_MAX_Y_POS = SCREEN_HEIGHT - 100

FINGER_HISTORY_LENGTH = 8
ARUCO_MARKER_ID_LIST = [0, 1, 2, 3]

cameraDevice = cv2.VideoCapture(0)

gameWindow = pyglet.window.Window(
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    caption="AR-Flappy"
)

arucoDictionaryObject = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
arucoDetectorObject = aruco.ArucoDetector(arucoDictionaryObject, aruco.DetectorParameters())

assetsFolderPath = Path(__file__).parent

birdSpriteFrameOne = loadImg(assetsFolderPath / "bird.png")
birdSpriteFrameTwo = loadImg(assetsFolderPath / "bird2.png")

pipeTextureImage = pyglet.image.load(str(assetsFolderPath / "pipe.png"))
backgroundImageRaw = pyglet.image.load(str(assetsFolderPath / "background_image.png"))
backgroundSprite = pyglet.sprite.Sprite(backgroundImageRaw)
backgroundSprite.scale_x = SCREEN_WIDTH / backgroundSprite.width
backgroundSprite.scale_y = SCREEN_HEIGHT / backgroundSprite.height

scoreLabelText = pyglet.text.Label(
    "0",
    font_size=28,
    x=10,
    y=SCREEN_HEIGHT - 34,
    anchor_x="left",
    anchor_y="baseline"
)

gameOverLabelText = pyglet.text.Label(
    "",
    font_size=28,
    x=SCREEN_WIDTH // 2,
    y=SCREEN_HEIGHT // 2,
    anchor_x="center",
    anchor_y="center",
    color=(255, 255, 255, 255)
)

standbyLabelText = pyglet.text.Label(
    "Show the ArUco marker sheet to start (RIGHT WAY UP!)",
    font_size=20,
    x=SCREEN_WIDTH // 2,
    y=35,
    anchor_x="center",
    anchor_y="baseline"
)

rawCameraFrameBgr = None

markersCurrentlyVisible = False
markersVisibleLastFrame = False
gameWasStartedOnce = False

fingerPositionHistoryDeque = deque(maxlen=FINGER_HISTORY_LENGTH)

currentBirdPositionTuple = (
    SCREEN_WIDTH // 4,
    SCREEN_HEIGHT // 2
)

currentScoreValue = 0
playerIsDead = False

pipeSpriteDeque = deque()
timeToNextPipeSpawn = 0.0

birdAnimationFrameIndex = 0
birdAnimationTimerSeconds = 0.0


def createNewPipePair():
    randomGapCenterY = random.randint(PIPE_MIN_Y_POS, PIPE_MAX_Y_POS)

    bottomRegion = pipeTextureImage.get_region(0, 0, pipeTextureImage.width, pipeTextureImage.height)
    bottomRegion.anchor_x = bottomRegion.width // 2
    bottomRegion.anchor_y = 0
    bottomPipeSprite = pyglet.sprite.Sprite(bottomRegion)
    bottomPipeSprite.x = SCREEN_WIDTH + bottomPipeSprite.width
    bottomPipeSprite.y = 0
    bottomPipeSprite.scale_x = 1.3
    bottomPipeSprite.scale_y = (randomGapCenterY - PIPE_GAP_HEIGHT_PIXELS // 2) / bottomRegion.height

    topRegion = pipeTextureImage.get_region(0, 0, pipeTextureImage.width, pipeTextureImage.height)
    topRegion.anchor_x = topRegion.width // 2
    topRegion.anchor_y = 0
    topPipeSprite = pyglet.sprite.Sprite(topRegion)
    topPipeSprite.rotation = 180
    topPipeSprite.x = bottomPipeSprite.x
    topPipeSprite.y = SCREEN_HEIGHT
    topPipeSprite.scale_x = 1.3
    topPipeSprite.scale_y = (SCREEN_HEIGHT - (randomGapCenterY + PIPE_GAP_HEIGHT_PIXELS // 2)) / topRegion.height

    pipeSpriteDeque.append({"bottom": bottomPipeSprite, "top": topPipeSprite, "scored": False})


def resetWholeGameState():
    global currentScoreValue
    global playerIsDead
    global pipeSpriteDeque
    global timeToNextPipeSpawn
    global currentBirdPositionTuple
    global fingerPositionHistoryDeque

    currentScoreValue = 0
    playerIsDead = False
    pipeSpriteDeque.clear()
    createNewPipePair()
    timeToNextPipeSpawn = time.time() + SECONDS_BETWEEN_PIPE_SPAWNS
    currentBirdPositionTuple = (SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2)
    fingerPositionHistoryDeque.clear()


@gameWindow.event
def on_key_press(pressedKeySymbol, _):
    global playerIsDead
    if pressedKeySymbol == pyglet.window.key.R and markersCurrentlyVisible:
        resetWholeGameState()


@gameWindow.event
def on_draw():
    gameWindow.clear()

    if not markersCurrentlyVisible:
        standbyImage = convertCvFrameToPyglet(rawCameraFrameBgr)
        if standbyImage:
            standbyImage.blit(0, 0, 0)
        standbyLabelText.draw()
        return

    backgroundSprite.draw()

    for pipePair in pipeSpriteDeque:
        pipePair["bottom"].draw()
        pipePair["top"].draw()

    activeBirdSprite = birdSpriteFrameOne if birdAnimationFrameIndex == 0 else birdSpriteFrameTwo
    activeBirdSprite.x = currentBirdPositionTuple[0]
    activeBirdSprite.y = currentBirdPositionTuple[1]
    activeBirdSprite.draw()

    scoreLabelText.text = str(currentScoreValue)
    scoreLabelText.draw()

    if playerIsDead:
        gameOverLabelText.text = f"GAME OVER (press R or cover ArUco code to restart) | Score: {currentScoreValue}"
        gameOverLabelText.draw()


def updateEveryFrame(deltaTimeSeconds):
    global rawCameraFrameBgr
    global markersCurrentlyVisible
    global markersVisibleLastFrame
    global gameWasStartedOnce
    global currentBirdPositionTuple
    global birdAnimationFrameIndex
    global birdAnimationTimerSeconds
    global currentScoreValue
    global playerIsDead
    global timeToNextPipeSpawn

    okFlag, cameraFrameOriginal = cameraDevice.read()
    if not okFlag:
        return
    rawCameraFrameBgr = cv2.resize(cameraFrameOriginal, (SCREEN_WIDTH, SCREEN_HEIGHT))

    grayFrame = cv2.cvtColor(cameraFrameOriginal, cv2.COLOR_BGR2GRAY)
    markerCorners, markerIds, _ = arucoDetectorObject.detectMarkers(grayFrame)

    markersFoundNow = markerIds is not None and len(markerIds) == 4

    if markersFoundNow and not markersVisibleLastFrame:
        if not gameWasStartedOnce or playerIsDead:
            resetWholeGameState()
            gameWasStartedOnce = True

    markersCurrentlyVisible = markersFoundNow
    markersVisibleLastFrame = markersFoundNow

    if not markersCurrentlyVisible:
        return

    fingertipPositionCandidate = None
    try:
        idList = [int(x) for x in markerIds.flatten()]
        markerDictionary = {}
        for indexNumber in range(len(idList)):
            markerDictionary[idList[indexNumber]] = markerCorners[indexNumber]

        everySinglePoint = []
        for mid in ARUCO_MARKER_ID_LIST:
            for cornerPoint in markerDictionary[mid][0]:
                everySinglePoint.append(cornerPoint)

        sumX = 0.0
        sumY = 0.0
        for onePoint in everySinglePoint:
            sumX += onePoint[0]
            sumY += onePoint[1]
        center_X = sumX / len(everySinglePoint)
        center_Y = sumY / len(everySinglePoint)

        innerFourPointsList = []
        for mid in ARUCO_MARKER_ID_LIST:
            candidateCorners = markerDictionary[mid][0]
            chosenPoint = candidateCorners[0]
            smallestDistance = float("inf")
            for pt in candidateCorners:
                deltaX = pt[0] - center_X
                deltaY = pt[1] - center_Y
                distanceValue = math.sqrt(deltaX * deltaX + deltaY * deltaY)
                if distanceValue < smallestDistance:
                    smallestDistance = distanceValue
                    chosenPoint = pt
            innerFourPointsList.append(chosenPoint)

        warpedCameraView = warpCameraImageToWholeScreen(cameraFrameOriginal, innerFourPointsList)
        fingertipPositionCandidate = findHighestVisibleFingertipCandidate(warpedCameraView)

    except:
        fingertipPositionCandidate = None

    if fingertipPositionCandidate:
        fingerPositionHistoryDeque.append(fingertipPositionCandidate)

    if fingerPositionHistoryDeque: #average finger pos to remove jumps
        sumX = 0
        sumY = 0
        for xVal, yVal in fingerPositionHistoryDeque:
            sumX += xVal
            sumY += yVal
        smoothX = int(sumX / len(fingerPositionHistoryDeque))
        smoothY = int(sumY / len(fingerPositionHistoryDeque))
        currentBirdPositionTuple = (smoothX, smoothY)

    bx, by = currentBirdPositionTuple
    if bx < BIRD_RADIUS_PIXELS:
        bx = BIRD_RADIUS_PIXELS
    if bx > SCREEN_WIDTH - BIRD_RADIUS_PIXELS:
        bx = SCREEN_WIDTH - BIRD_RADIUS_PIXELS
    if by < BIRD_RADIUS_PIXELS:
        by = BIRD_RADIUS_PIXELS
    if by > SCREEN_HEIGHT - BIRD_RADIUS_PIXELS:
        by = SCREEN_HEIGHT - BIRD_RADIUS_PIXELS
    currentBirdPositionTuple = (bx, by)

    birdAnimationTimerSeconds += deltaTimeSeconds
    if birdAnimationTimerSeconds >= 0.1:
        birdAnimationFrameIndex = 1 - birdAnimationFrameIndex
        birdAnimationTimerSeconds = 0.0

    if playerIsDead:
        return

    currentTimeNow = time.time()
    while currentTimeNow >= timeToNextPipeSpawn:
        createNewPipePair()
        newInterval = max(1.0, SECONDS_BETWEEN_PIPE_SPAWNS - 0.08 * currentScoreValue)
        timeToNextPipeSpawn += newInterval

    for pipePair in list(pipeSpriteDeque):
        deltaMove = (PIPE_HORIZONTAL_SPEED + currentScoreValue * 8) * deltaTimeSeconds
        pipePair["bottom"].x -= deltaMove
        pipePair["top"].x -= deltaMove

        frontEdgeX = pipePair["bottom"].x + pipePair["bottom"].width // 2
        if not pipePair["scored"] and frontEdgeX < bx:
            pipePair["scored"] = True
            currentScoreValue += 1

        if pipePair["bottom"].x + pipePair["bottom"].width < -50:
            pipeSpriteDeque.popleft()

    for pipePair in pipeSpriteDeque:
        leftEdgeX = pipePair["bottom"].x - pipePair["bottom"].width // 2
        rightEdgeX = pipePair["bottom"].x + pipePair["bottom"].width // 2

        insidePipeHoriz = (bx + BIRD_RADIUS_PIXELS > leftEdgeX) and (bx - BIRD_RADIUS_PIXELS < rightEdgeX)
        if insidePipeHoriz:
            gapTopY = pipePair["bottom"].height
            gapBottomY = gapTopY + PIPE_GAP_HEIGHT_PIXELS
            hitTopPart = by - BIRD_RADIUS_PIXELS < gapTopY
            hitBottomPart = by + BIRD_RADIUS_PIXELS > gapBottomY
            if hitTopPart or hitBottomPart:
                playerIsDead = True
                break

    if by - BIRD_RADIUS_PIXELS <= 0 or by + BIRD_RADIUS_PIXELS >= SCREEN_HEIGHT:
        playerIsDead = True


pyglet.clock.schedule_interval(updateEveryFrame, 1 / 120)
pyglet.app.run()
