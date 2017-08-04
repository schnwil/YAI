Yet Another Image converts PNG images into dithered and posterized  images that can be displayed on OpenComputer displays (T3 only) for MC 1.7.10.

Dependencies for the converter include Python 3.2 or greater, PIL and Numpy.

You need only call highRes or lowRes methods from the converter (lowRes does not support dithering).

To display the image move the byte file to your OC drive and make sure the image.lua is in the /lib directory. From here you only need to call image.imshow(<path_to_file>). Image.lua also contains some other functionality such as offsetting the image, cropping, resetting the screen and more.