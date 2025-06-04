import cv2
import numpy as np
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", required=True)
parser.add_argument("-o", "--output", required=True)
parser.add_argument("--width", type=int, required=True)
parser.add_argument("--height", type=int, required=True)
args = parser.parse_args()

image = cv2.imread(args.input)
if image is None:
    print("Cannot open image:", args.input)
    sys.exit(1)

display = image.copy()
points = []

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))
        cv2.circle(display, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Ecken Auswählen", display)

cv2.namedWindow("Ecken Auswählen")
cv2.setMouseCallback("Ecken Auswählen", mouse_callback)

while True:
    cv2.imshow("Ecken Auswählen", display)
    key = cv2.waitKey(1) & 0xFF

    if key == 27:#esc reset
        points = []
        display = image.copy()

    if len(points) == 4:
        w=args.width;
        h=args.height
        src = np.float32(points)
        dst = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(image, M, (w, h))

        text = "Press s to save, ESC to try again"
        tmp = warped.copy()
        cv2.putText(tmp, text, (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
        cv2.imshow("transformedRect", tmp)
        while True:
            key2 = cv2.waitKey(0)
            if key2 == ord('s'):
                cv2.imwrite(args.output, warped)
                print("Saved to", args.output)
                cv2.destroyAllWindows()
                sys.exit(0)
            elif key2 == 27:
                cv2.destroyWindow("transformedRect")
                points = []
                display = image.copy()
                break

    if cv2.getWindowProperty("Ecken Auswählen", cv2.WND_PROP_VISIBLE) < 1:
        break

cv2.destroyAllWindows()
