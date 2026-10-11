import cv2
img = cv2.imread('real_test.webp')
if img is not None:
    print('Shape:', img.shape)
else:
    print('Could not read image')
