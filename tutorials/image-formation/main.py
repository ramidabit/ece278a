# notes
"""
Created on Wed Feb 2 12:00:00 2022

@author: sean mackenzie, rami dabit, and peter li
"""

# imports
import streamlit as st
from PIL import Image, ImageFilter, ImageEnhance
import cv2 as cv
import numpy as np
import scipy.ndimage

from skimage import data, util, io
from skimage.exposure import rescale_intensity
from skimage import data
from skimage import transform
from skimage.transform import warp, AffineTransform
from skimage.draw import ellipse

from os import path
from scipy import optimize as opt
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib import patches
import requests
from io import BytesIO
import urllib


def main():
    selected_box = st.sidebar.selectbox(
        'Choose one of the following',
        ('Welcome', 'Pinhole Camera Model', 'Paraxial Camera Model', 'Homography',
         'Camera Intrinsics', 'Camera Extrinsics')
    )

    if selected_box == 'Welcome':
        welcome()

    if selected_box == 'Pinhole Camera Model':
        pinhole_camera_model()

    if selected_box == 'Paraxial Camera Model':
        paraxial_camera_model()

    if selected_box == 'Homography':
        homography()

    if selected_box == "Camera Intrinsics":
        camera_intrinsics()
        
    if selected_box == "Camera Extrinsics":
        camera_intrinsics()


def welcome():
    st.title('Hi there, welcome to our web app on Image Formation!')

    st.subheader('ECE 278A: Digital Image Processing')
    st.subheader('University of California, Santa Barbara')
    st.subheader('Sean MacKenzie, Rami Dabit, and Peter Li')
    st.subheader('Feel free to interact with our web app. :)')

    # st.image('hackershrine.jpg',use_column_width=True)


def load_image(filename):
    image = cv.imread(filename)
    return image


# One-time preprocessing for pinhole camera model
# Download images to avoid doing so repetitively
urllib.request.urlretrieve("https://i.imgur.com/MHlfq0o.png", "subj.png")
url_bg = "https://wallpapercave.com/wp/JYodMo6.jpg"
response_bg = requests.get(url_bg)
dataBytesIO_bg = BytesIO(response_bg.content)
bg = Image.open(dataBytesIO_bg)
# One-time preprocessing
subj_w_bg = cv.imread("subj.png", 1)
temp = cv.cvtColor(subj_w_bg, cv.COLOR_BGR2GRAY)
_, alpha = cv.threshold(temp, 0, 255, cv.THRESH_BINARY)
b, g, r = cv.split(subj_w_bg)
rgba = [b, g, r, alpha]
dest = cv.merge(rgba, 4)
cv.imwrite("pinhole_temp.png", dest)
subj = Image.open("pinhole_temp.png")

# Helper function to simulate real-world camera capture
def capture(background, subject, val, focus):
    # Blur background/foreground to simulate a change in focus
    if focus == 0:
        background = background.filter(ImageFilter.GaussianBlur(radius=val))
    else:
        subject = subject.filter(ImageFilter.GaussianBlur(radius=val))

    # Horizontal and vertical spacing with bicubic resampling
    #img.thumbnail((400, 400), resample=Image.BICUBIC)

    # Convert images to RGBA
    subj1 = subject.convert("RGBA")
    bg1 = background.convert("RGBA")
    # Center our gaucho image along the background
    width = (bg1.width - subj1.width) // 2
    height = (bg1.height - subj1.height) // 2
    # Paste gaucho at the center
    bg1.paste(subj1, (width, height), subj1)
    bg1.save("merged.png", format="png")
    # Reopen the merged ('faux capture') image
    return Image.open("merged.png")

def pinhole_camera_model():
    """
    Author: Rami Dabit
    :return:
    """
    st.title("Pinhole Camera Model: Sensor View")

    x = st.slider('Adjust the camera aperature (f-number)',min_value=2,max_value=64,value=16)
    f = st.slider('Adjust the focal length of the lens (mm)',min_value=10,max_value=300,value=50)

    foc = st.radio(
        "Focus select",
        ('Foreground','Background'))
    if foc == 'Foreground':
        image = capture(bg,subj,65-x,0)
    else:
        image = capture(bg,subj,65-x,1)

    width, height = image.size
    # If we zoom in while keeping the aperture constant, the background becomes more blurred.

    if f < 35:
        k_1 = 0.4
        k_2 = 0.1

        # Meshgrid for interpolation mapping
        x,y = np.meshgrid(np.float32(np.arange(width)),np.float32(np.arange(height)))

        # Center and scale grid for radius calculation
        x_c = width/2 
        y_c = height/2 
        x = x - x_c
        y = y - y_c
        x = x / x_c
        y = y / y_c
        radius = np.sqrt(x**2 + y**2)

        # Radial distortion model
        m_r = 1 + k_1*radius + k_2*radius**2
        # Apply model
        x= x * m_r
        y = y * m_r
        # Reset shifts
        x = x*x_c + x_c
        y = y*y_c + y_c

        image = np.asarray(image)
        distorted = np.zeros(image.shape)
        distorted0 = scipy.ndimage.map_coordinates(image[:,:,0], [y.ravel(),x.ravel()])
        distorted1 = scipy.ndimage.map_coordinates(image[:,:,1], [y.ravel(),x.ravel()])
        distorted2 = scipy.ndimage.map_coordinates(image[:,:,2], [y.ravel(),x.ravel()])
        distorted3 = scipy.ndimage.map_coordinates(image[:,:,3], [y.ravel(),x.ravel()])

        distorted = np.dstack((distorted2, distorted1, distorted0, distorted3))
        distorted.resize(image.shape)

        cv.imwrite("distorted.png",distorted)
        image = Image.open("distorted.png")
    
    image = image.crop((2*f, 0, width-2*f, height-np.floor(3*f/2)))

    eso = st.slider('Adjust camera exposure (ESO)',min_value=0.0,max_value=2.0,value=1.0)
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(eso)

    image.save("res_img.png", format="png")
    st.image(Image.open("res_img.png"), use_column_width=True,clamp = True)


def paraxial_camera_model():
    """
    Author: Sean MacKenzie
    :return:
    """
    # introduction
    st.title("Paraxial Refraction Model")
    st.subheader("An ideal mapping from 3D objects points (the real world) to 2D image points (your iPhone screen)")

    st.text("Consider a 3D point,")
    st.latex(r'p \: = \: [x, y, z,]^T')

    st.text("The lens focuses light onto a sensor. There is a specific distance at which \n"
            "objects are 'in-focus'.")

    pic_paraxial_camera_model = io.imread('tutorials/image-formation/paraxial_camera_model_pic.png')
    st.image(pic_paraxial_camera_model, use_column_width=True)

    st.text("The 3D to 2D projection defined by the paraxial refraction model is,")
    st.latex(r' \acute p \: = \: [\acute x \quad \acute y]^T \: ='
             r' \: [(f + z_0)\frac{x}{z} \quad (f + z_0)\frac{y}{z}]^T')
    st.caption("Note: these are inhomogeneous coordinates.")

    st.text("In the paraxial refraction model, the lens focuses light rays that are parallel \n"
            "(to the optical axes) to the focal point.")

    st.header("Interactive Paraxial Refraction Camera Model")

    st.subheader("Prompts to consider:")
    st.text("1. Parallel rays are focused to the focal point but, when would rays from \n"
            "an object ever be parallel to the lens?")

    st.text("2. Most real-world cameras (e.g. a laboratory microscope with a photographic \n "
            "film) don't position the sensor exactly at the focal plane. Why is this?")

    st.subheader("Toggles")


    # optics
    f = st.slider(label='Change camera lens focal length', min_value=50, max_value=200, value=100)
    d = st.slider(label='Change camera lens diameter', min_value=25, max_value=45, value=35)

    # ccd
    ccd_z = st.slider(label='Change camera sensor position', min_value=-110, max_value=-100, value=-102)
    ccd_h = st.slider(label='Change camera sensor size', min_value=2, max_value=20, value=10)

    # object
    zo = st.slider(label='Change object distance', min_value=100, max_value=10000, value=500)
    yo = st.slider(label='Change object height', min_value=-20, max_value=20, value=(-15, -16))
    yo_num = st.slider(label='Change number of object points', min_value=1, max_value=20, value=1)

    def model_pinhole(zo, yo, zi):
        yi = zi * yo / zo
        return yi

    def thin_lens_model(zo, f=f):
        zi = 1 / (1 / f - 1 / zo)
        return zi

    # shape of the lens
    def add_lens_patch(width, height, xcenter=0, ycenter=0, angle=0):
        theta = np.deg2rad(np.arange(0.0, 360.0, 1.0))
        x = 0.5 * width * np.cos(theta)
        y = 0.5 * height * np.sin(theta)

        rtheta = np.radians(angle)
        R = np.array([
            [np.cos(rtheta), -np.sin(rtheta)],
            [np.sin(rtheta), np.cos(rtheta)],
        ])

        x, y = np.dot(R, [x, y])
        x += xcenter
        y += ycenter

        return patches.Ellipse((xcenter, ycenter), width, height, angle=angle,
                               linewidth=0.5, fill=True, color='gray', alpha=0.125)

    def model_paraxial_lens(zo, yo, f, d, ccd_z, ccd_h):

        if isinstance(yo, (int, float)):
            yo = [yo]

        # create figure
        fig = plt.figure(figsize=(14, 7))
        gs = GridSpec(1, 3, figure=fig)
        ax1 = plt.subplot(gs[0, :-1])
        ax1.margins(0.01)
        ax2 = plt.subplot(gs[0, -1])
        ax1.margins(0.01)

        # optical axis
        ax1.axhline(0, color='black', linewidth=0.5, alpha=0.5, zorder=1.5)
        ax2.axhline(0, color='black', linewidth=0.5, alpha=0.5, zorder=1.5)

        # lens
        for width, ax in zip([f / 10, zo / 5.555], [ax1, ax2]):
            ax.add_patch(add_lens_patch(width=width, height=d))
            ax.add_patch(add_lens_patch(width=width, height=d))

        # ccd
        ax1.plot([ccd_z, ccd_z], [-ccd_h / 2, ccd_h / 2], color='black', linewidth=3, alpha=0.25, label='Film',
                 zorder=1.5)

        # focal plane
        ax1.plot([-f, -f], [-ccd_h / 2, ccd_h / 2], color='black', linestyle='--', alpha=0.125, label='Focal Plane')

        # initialize
        counter = 0
        yo_i_i = 0
        yi_i = 0

        for i, yo_i in enumerate(yo):

            # in focus axial position
            zi = thin_lens_model(zo, f)

            # in focus height
            yi = model_pinhole(zo, yo_i, zi)

            # angle of light cone
            theta = np.arcsin(d / (2 * zo))

            # invert for plotting
            zi = -zi
            yi = -yi

            # store initial value
            if i == 0:
                yo_i_i = yo_i
                yi_i = yi

            # rays - object
            ray_obj_z = [zo, 0]
            ray_obj_top = [yo_i, d / 2]
            ray_obj_center = [yo_i, 0]
            ray_obj_bottom = [yo_i, -d / 2]

            # rays - image
            ray_img_z = [0, zi]
            ray_img_top = [d / 2, yi]
            ray_img_center = [0, yi]
            ray_img_bottom = [-d / 2, yi]

            # rays intersecting at ccd
            ray_ccd_top = -(d / 2 - yi) * ccd_z / zi + d / 2
            ray_ccd_center = yi * ccd_z / zi
            ray_ccd_bottom = -(-d / 2 - yi) * ccd_z / zi - d / 2

            # conditional labeling
            if i == len(yo) - 1:
                ax1.scatter(zi, yi, color='blue', label='Image')
                ax2.scatter(zo, yo_i, color='red', label='Object')
            else:
                ax1.scatter(zi, yi, color='blue')
                ax2.scatter(zo, yo_i, color='red')

            # image formation
            ax1.plot([zi, zi], [yi_i, yi], color='blue', linestyle=':', linewidth=2)
            ax1.plot(ray_img_z, ray_img_top, color='blue', alpha=0.25)
            ax1.plot(ray_img_z, ray_img_center, color='blue', alpha=0.25)
            ax1.plot(ray_img_z, ray_img_bottom, color='blue', alpha=0.25)

            # object formation
            ax2.plot([zo, zo], [yo_i_i, yo_i], color='red', linestyle=':', linewidth=2)
            ax2.plot(ray_obj_z, ray_obj_top, color='red', alpha=0.25)
            ax2.plot(ray_obj_z, ray_obj_center, color='red', alpha=0.25)
            ax2.plot(ray_obj_z, ray_obj_bottom, color='red', alpha=0.25)

            # rays intersecting ccd
            for ray_ccd in [ray_ccd_top, ray_ccd_center, ray_ccd_bottom]:
                if -ccd_h / 2 < ray_ccd < ccd_h / 2:
                    if counter == 0:
                        ax1.scatter(ccd_z, ray_ccd, marker='.', color='green', alpha=0.99, label=r'$Ray_{sensor}$')
                        counter = counter + 1
                    else:
                        ax1.scatter(ccd_z, ray_ccd, marker='.', color='green', alpha=0.99)

        # figure formatting
        ax1.set_xlim([-150, 0])
        ax1.set_ylim([-25, 25])
        ax1.tick_params(axis='both', labelsize=14)
        ax1.set_xlabel(r'Distance $_{image \: plane}$', fontsize=18)
        ax1.set_ylabel('Height', fontsize=18)

        ax2.set_xlim([0, zo * 1.25])
        ax2.set_ylim([-25, 25])
        ax2.yaxis.set_label_position("right")
        ax2.yaxis.tick_right()
        ax2.tick_params(axis='both', labelsize=14)
        ax2.set_xlabel(r'Distance $_{object \: plane}$', fontsize=18)

        ax1.legend(loc='upper left', fontsize=18)
        ax2.legend(loc='upper right', fontsize=18)

        plt.subplots_adjust(wspace=.001)
        plt.show()
        st.pyplot(fig=fig)

        return zi, yi, theta

    if yo_num == 1:
        yoi = np.mean(yo)
    else:
        yoi = np.linspace(np.min(yo), np.max(yo), yo_num)
    zi, yi, theta = model_paraxial_lens(zo, yoi, f, d, ccd_z, ccd_h)

    image_position_string = "Image height yi = {} at axial distance zi = {}".format(np.round(-yi, 2), np.round(-zi, 2))
    numerical_aperture_string = "Viewing angle = {} degrees".format(np.round(theta * 360 / (2 * np.pi), 2))

    st.caption(body=image_position_string)
    st.caption(body=numerical_aperture_string)


def homography():
    """
    Author: Peter Li
    :return:
    """
    st.title("Image Formation: Homography")

    # ========================================================
    # my own start

    url = 'https://images.unsplash.com/photo-1613048998835-efa6e3e3dc1b?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1074&q=80'

    response = requests.get(url)
    imgfile = Image.open(BytesIO(response.content))
    img = np.array(imgfile)

    if st.button('Original Image'):
        # [Remind] use st.image to plot
        st.image(img, use_column_width=True)

    my_phi = st.slider('Change angle to decide camera position', min_value=-35, max_value=35, value=0)
    my_k = st.slider('Change Value to zoon in or zoom out', min_value=-0.2, max_value=1.0, value=0.2)

    # Setting Parameter
    # phi = 25 # [-70~70]
    # unit degree
    phi = my_phi
    scale_factor = 1  # (this is optional)

    # k = 0.7 # need to be positive-value
    k = my_k
    b = 0.5  # fix

    increment = ((k + b) / b) * np.tan((phi / 180) * 3.14)
    l_side = np.sqrt(((k + b) / b) ** 2 + (k + b) ** 2) + increment
    r_side = np.sqrt(((k + b) / b) ** 2 + (k + b) ** 2) - increment

    origin_len = img.shape[0] / 2
    origin_wid = img.shape[1] / 2

    transform_center = [origin_wid, origin_len]

    transform_l = (np.sqrt(1 + b ** 2) / l_side) * origin_len
    transform_r = (np.sqrt(1 + b ** 2) / r_side) * origin_len
    transform_wid = origin_wid * (b / (k + b))

    # source coordinates
    src_i = np.array([0, 0,
                      0, img.shape[0],
                      img.shape[1], img.shape[0],
                      img.shape[1], 0, ]).reshape((4, 2))

    # destination coordinates
    dst_i = np.array(
        [transform_center[0] - transform_wid * scale_factor, transform_center[1] - transform_l * scale_factor,
         transform_center[0] - transform_wid * scale_factor, transform_center[1] + transform_l * scale_factor,
         transform_center[0] + transform_wid * scale_factor, transform_center[1] + transform_r * scale_factor,
         transform_center[0] + transform_wid * scale_factor,
         transform_center[1] - transform_r * scale_factor, ]).reshape((4, 2))

    # using skimage’s transform module where ‘projective’ is our desired parameter
    tform = transform.estimate_transform('projective', src_i, dst_i)
    tf_img = transform.warp(img, tform.inverse)

    # plotting the original image
    plt.imshow(img)

    # plotting the transformed image
    fig, ax = plt.subplots()
    ax.imshow(tf_img)
    _ = ax.set_title('projective transformation')
    plt.plot(transform_center[0], transform_center[1], 'x')
    plt.show()

    # streamlit explanation
    if my_phi > 0:
        direction_string = "rotate from original position to right at " + str(my_phi)+ " degrees."
    elif my_phi < 0:
        direction_string = "rotate from original position to left at " + str(-my_phi)+ " degrees."
    else:
        direction_string = "is at original position ."

    if my_k > 0:
        distance_string = " Zoom out."
    elif my_k < 0:
        distance_string = " Zoom in."
    else:
        distance_string = " No zoom in/out." 

    string_camera_posi = " Camera {} ".format(direction_string)
    string_zoomInOut  = "  {} ".format(distance_string)

    st.caption(body=string_camera_posi)
    st.caption(body=string_zoomInOut)



    # [Remind] use st.image to plot
    st.image(tf_img, use_column_width=True)

    # my own end
    # ========================================================


def camera_intrinsics():
    """
    Author: Sean MacKenzie
    References:
    [1] Zhang's camera calibration
    [2] Burger's
    [3] Blog
    :return:
    """

    # introduction
    st.title("Camera Intrinsic Parameters")
    st.subheader("A mapping from 3D objects points (the real world) to 2D image points (your iPhone screen)")

    st.subheader("Refining the idealized paraxial model for a real camera (including optical distortions)")
    st.caption("Note: Optical distortions (non-idealized lens) motivate the need for camera calibration, \n"
               "however, we do not investigate optical distortions here.")

    st.text("An accurate model of the image projection parameters for a real optical system is \n"
            "necessary for quantitative geometric measurement in computer vision applications.")
    st.caption("An example application is the Microsoft Kinect for movement tracking.")
    st.text("In order to develop an accurate camera model, we must calibrate the camera.")

    # setup the camera model: inhomogeneous coordinates
    st.subheader("Camera model: inhomogeneous coordinates")
    st.text("Again, consider a 3D point,")
    st.latex(r'p \: = \: [x, y, z,]^T')

    st.text("The lens focuses light onto a sensor. There is a specific distance at which \n"
            "objects are 'in-focus'.")

    pic_paraxial_camera_model = io.imread('tutorials/image-formation/paraxial_camera_model_pic.png')
    st.image(pic_paraxial_camera_model, use_column_width=True)

    st.text("The 3D to 2D projection defined by the paraxial refraction model is,")
    st.latex(r' \acute p \: = \: [\acute x \quad \acute y]^T \: ='
             r' \: [(f + z_0)\frac{x}{z} + c_x \quad (f + z_0)\frac{y}{z} + c_y]^T')
    st.text("where c_x and c_y describe how image plane and digital image coordinates differ \n"
            "by a translation.")
    st.caption("Note: these are inhomogeneous coordinates. They describe the nonlinear \n"
               "transformations in the domain of Cartesian coordinates.")

    # setup the camera model: homogeneous coordinates
    st.subheader("Camera model: homogeneous coordinates")
    st.text("We rewrite the perspective transformation as a linear matrix equation,")
    st.latex(r'\begin {pmatrix} x \\ y \end {pmatrix} \equiv '
             r'\begin {pmatrix} fX/Z \\ fY/Z \\ 1 \end {pmatrix} \equiv'
             r'\begin {pmatrix} fX \\ fY \\ Z \end {pmatrix}  ='
             r'\underbrace{ '
             r'\begin {pmatrix} f & 0 & 0 & 0 \\ 0 & f & 0 & 0 \\ 0 & 0 & 1 & 0 \end {pmatrix} '
             r'}_\text{Mp}'
             r'\cdot \begin {pmatrix} X \\ Y \\ Z \\ 1 \end {pmatrix}')
    st.caption("Note: here, we first formulate a projection matrix for an ideal camera.")

    st.text("The projection matrix Mp can be decomposed into two matrices Mf and Mo,")
    st.latex(r'Mp = '
             r'\underbrace{ '
             r'\begin {pmatrix} f & 0 & 0 \\ 0 & f & 0 \\ 0 & 0 & 1 \end {pmatrix} '
             r'}_\text{Mf}'
             r'\cdot '
             r'\underbrace{ '
             r'\begin {pmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \end {pmatrix} '
             r'}_\text{Mo}'
             r'= Mf \cdot Mo'
             )
    st.text("where Mf models the camera lens and Mo describes the transformation from \n"
            "camera coordinates to real world coordinates when the object is positioned \n"
            "along the optical axis.")

    st.text("If the object is not positioned along the optical axis, the camera observes \n"
            "3D that were subjected to rigid body motion. This is formulated as,")
    st.latex(r'\begin {pmatrix} x \\ y \end {pmatrix} = hom^{-1} \left['
             r'\underbrace{ '
             r'\begin {pmatrix} f & 0 & 0 \\ 0 & f & 0 \\ 0 & 0 & 1 \end {pmatrix} '
             r'}_\text{Mf} \cdot'
             r'\underbrace{ '
             r'\begin {pmatrix} r_{11} & r_{12} & r_{13} & t_{x} \\ r_{21} & r_{22} & r_{23} & t_{y} \\ r_{31} & r_{32} & r_{33} & t_{z} \end {pmatrix} '
             r'}_\text{Rt}'
             r'\cdot \begin {pmatrix} X \\ Y \\ Z \\ 1 \end {pmatrix} \right]')

    st.subheader("Intrinsic camera parameters")
    st.text("We finally define how x/y-coordinates on the image plane map to pixel \n"
            "coordinates on the sensor (variable, \"u\").")
    st.latex(r'\begin {pmatrix} u \\ v \end {pmatrix} = hom^{-1} \left['
             r'\underbrace{ '
             r'\begin {pmatrix} s_x & s_{\theta} & u_c \\ 0 & s_y & v_c \\ 0 & 0 & 1 \end {pmatrix} \cdot'
             r'\begin {pmatrix} f & 0 & 0 \\ 0 & f & 0 \\ 0 & 0 & 1 \end {pmatrix} '
             r'}_\text{A}'
             r'\cdot \begin {pmatrix} x \\ y \\ 1 \end {pmatrix} \right]')
    st.text("where ")
    st.latex(r'A = \begin {pmatrix} fs_x & fs_{\theta} & u_c \\ 0 & fs_y & v_c \\ 0 & 0 & 1 \end {pmatrix} ='
             r'\begin {pmatrix} \alpha & \gamma & u_c \\ 0 & \beta & v_c \\ 0 & 0 & 1 \end {pmatrix}')
    st.text(" is the intrinsic camera matrix.")

    st.text("The complete perspective imaging transformation can now be written as ")
    st.latex(r'\begin {pmatrix} u \\ v \end {pmatrix} = hom^{-1} \left['
             r'\underbrace{ '
             r'\begin {pmatrix} \alpha & \gamma & u_c \\ 0 & \beta & v_c \\ 0 & 0 & 1 \end {pmatrix}'
             r'}_\text{A} \cdot'
             r'\underbrace{ '
             r'\begin {pmatrix} r_{11} & r_{12} & r_{13} & t_{x} \\ r_{21} & r_{22} & r_{23} & t_{y} \\ r_{31} & r_{32} & r_{33} & t_{z} \end {pmatrix} '
             r'}_\text{Rt} \cdot'
             r'\begin {pmatrix} X \\ Y \\ Z \\ 1 \end {pmatrix} \right]')

    st.text("where A captures the intrinsic parameters of the camera and Rt are the extrinsic parameters.\n"
            "The intrinsic parameters describe how world coordinates map to sensor coordinates while \n"
            "the extrinsic parameters describe the projection transformation between the world and \n"
            "sensor coordinate axes.")

    st.header("Demonstration of Camera Intrinsic Parameters")

    st.subheader("Camera calibration")
    st.text("We will calculate the intrinsic parameters using \"plane-based self calibration.\"")

    fig, [ax1, ax2, ax3, ax4] = plt.subplots(ncols=4, figsize=(13, 3.5))
    for i, ax in enumerate([ax1, ax2, ax3, ax4]):
        pic_cb = io.imread('tutorials/image-formation/syn_chessboard_4x4_{}.tif'.format(i + 1))
        ax.imshow(pic_cb)
        ax.axis('off')
        ax.set_title('Image #1', fontsize=10)
    plt.suptitle("Plane-based self calibration using chessboards")
    plt.show()
    st.pyplot(fig=fig)


    st.subheader("Toggles")

    num_images = st.slider(label='Change number of calibration images used to compute the intrinsic parameters.',
                           min_value=2, max_value=4, value=3)

    # calculate camera intrinsic parameters

    # chessboard pattern and size
    pattern_dim = (4, 5)
    square_dim = 1.0

    def generate_synthetic_chessboards(image_number=1, save_image=False, scale=1.0, rotate_degrees=0, shear=0.0,
                                       translate_x=0, translate_y=0):

        # sizes
        cb_size_x = 149  # checkerboard: number of rows, where one row is 30 pixels wide (range: 75:25:175)
        cb_size_y = 124  # checkerboard: number of columns, where one columns is 30 pixels tall (range: 75:25:175)
        cb_shape_x = 512  # image shape: number of columns
        cb_shape_y = 512  # image shape: number of rows

        # transformations
        #scale = 1.8
        scale_x = scale  # stretch in +x-dir. (do not use - unrealistic stretching)
        scale_y = scale  # stretch in +y-dir. (do not use - unrealistic stretching)

        #rotate_degrees = -30  # rotation in clockwise-dir. (range: 0:360)
        rotation = rotate_degrees * 2 * np.pi / 360

        #shear = 0.2  # shear in clockwise-dir. (range: -0.8:0.1:0.8)

        #translate_x = -100  # translation in +x-dir. (range: 0:cb_shape_x - cb_size_x)
        #translate_y = 40  # translation in +y-dir. (range: 0:cb_shape_y - cb_size_y)
        trans_x = cb_shape_y // 2 - cb_size_y // 2 + translate_x
        trans_y = cb_shape_x // 2 - cb_size_x // 2 + translate_y

        # Transformed checkerboard
        tform = AffineTransform(scale=(scale_x, scale_y), rotation=rotation, shear=shear,
                                translation=(trans_x, trans_y))
        image = warp(data.checkerboard()[:cb_size_x, :cb_size_y], tform.inverse, output_shape=(cb_shape_y, cb_shape_x))

        # rescale to 16-bit
        image = rescale_intensity(image, out_range=np.uint16)

        fig, ax = plt.subplots()
        ax.imshow(image, cmap=plt.cm.gray)
        ax.axis((0, cb_shape_x, cb_shape_y, 0))
        plt.show()
        st.image(image, use_column_width=True)

        if save_image:
            io.imsave('syn_chessboard_4x4_{}.tif'.format(image_number), image)

    def get_camera_images(num_images=4):
        images = ['tutorials/image-formation/syn_chessboard_4x4_{}.tif'.format(each) for each in np.arange(1, num_images + 1)]
        images = sorted(images)
        for each in images:
            yield (each, cv.imread(each, 0))

    def getChessboardCorners(images=None, visualize=False, num_images=4):
        objp = np.zeros((pattern_dim[1] * pattern_dim[0], 3), dtype=np.float64)
        objp[:, :2] = np.indices(pattern_dim).T.reshape(-1, 2)
        objp *= square_dim

        chessboard_corners = []
        image_points = []
        object_points = []
        correspondences = []
        counter = 0
        for (path, each) in get_camera_images(num_images=num_images):  # images:

            if np.mean(each) < np.max(each // 2):
                each = cv.bitwise_not(each)

            ret, corners = cv.findChessboardCorners(each, patternSize=pattern_dim)
            if ret:
                corners = corners.reshape(-1, 2)

                if corners.shape[0] == objp.shape[0]:
                    image_points.append(corners)
                    object_points.append(objp[:, :-1])
                    assert corners.shape == objp[:, :-1].shape, "mismatch shape corners and objp[:,:-1]"
                    correspondences.append([corners.astype(int), objp[:, :-1].astype(int)])

                if visualize:
                    # Draw and display the corners
                    ec = cv.cvtColor(each, cv.COLOR_GRAY2BGR)
                    cv.drawChessboardCorners(ec, pattern_dim, corners, ret)

                    # to show via skimage
                    fig, ax = plt.subplots(figsize=(4,4))
                    ax.imshow(ec)
                    plt.show()
                    st.image(ec, use_column_width=False)
            else:
                print("Error in detection points: ", counter)

            counter += 1

        return correspondences

    def compute_view_based_homography(correspondence, reproj=False):
        """
        correspondence = (imp, objp, normalized_imp, normalized_objp, N_u, N_x, N_u_inv, N_x_inv)
        """
        image_points = correspondence[0]
        object_points = correspondence[1]
        normalized_image_points = correspondence[2]
        normalized_object_points = correspondence[3]
        N_u = correspondence[4]
        N_x = correspondence[5]
        N_u_inv = correspondence[6]
        N_x_inv = correspondence[7]

        N = len(image_points)
        M = np.zeros((2 * N, 9), dtype=np.float64)

        # create row wise allotment for each 0-2i rows
        for i in range(N):
            X, Y = normalized_object_points[i]  # A
            u, v = normalized_image_points[i]  # B

            row_1 = np.array([-X, -Y, -1, 0, 0, 0, X * u, Y * u, u])
            row_2 = np.array([0, 0, 0, -X, -Y, -1, X * v, Y * v, v])
            M[2 * i] = row_1
            M[(2 * i) + 1] = row_2

        # M.h  = 0 . solve system of linear equations using SVD
        u, s, vh = np.linalg.svd(M)

        h_norm = vh[np.argmin(s)]
        h_norm = h_norm.reshape(3, 3)

        # h = h_norm
        h = np.matmul(np.matmul(N_u_inv, h_norm), N_x)

        # if abs(h[2, 2]) > 10e-8:
        h = h[:, :] / h[2, 2]

        # print("Normalized Homography Matrix for View : \n", h_norm)
        # print("Homography for View : \n", h)

        return h

    def normalize_points(chessboard_correspondences):
        views = len(chessboard_correspondences)

        def get_normalization_matrix(pts, name="A"):
            pts = pts.astype(np.float64)
            x_mean, y_mean = np.mean(pts, axis=0)
            var_x, var_y = np.var(pts, axis=0)
            s_x, s_y = np.sqrt(2 / var_x), np.sqrt(2 / var_y)
            n = np.array([[s_x, 0, -s_x * x_mean], [0, s_y, -s_y * y_mean], [0, 0, 1]])

            n_inv = np.array([[1. / s_x, 0, x_mean], [0, 1. / s_y, y_mean], [0, 0, 1]])
            return n.astype(np.float64), n_inv.astype(np.float64)

        ret_correspondences = []
        for i in range(views):
            imp, objp = chessboard_correspondences[i]
            N_x, N_x_inv = get_normalization_matrix(objp, "A")
            N_u, N_u_inv = get_normalization_matrix(imp, "B")

            # convert imp, objp to homogeneous
            hom_imp = np.array([[[each[0]], [each[1]], [1.0]] for each in imp])
            hom_objp = np.array([[[each[0]], [each[1]], [1.0]] for each in objp])

            normalized_hom_imp = hom_imp
            normalized_hom_objp = hom_objp

            for i in range(normalized_hom_objp.shape[0]):
                # 54 points iterate one by one & all points are homogeneous
                n_o = np.matmul(N_x, normalized_hom_objp[i])
                normalized_hom_objp[i] = n_o / n_o[-1]

                n_u = np.matmul(N_u, normalized_hom_imp[i])
                normalized_hom_imp[i] = n_u / n_u[-1]

            normalized_objp = normalized_hom_objp.reshape(normalized_hom_objp.shape[0], normalized_hom_objp.shape[1])
            normalized_imp = normalized_hom_imp.reshape(normalized_hom_imp.shape[0], normalized_hom_imp.shape[1])

            normalized_objp = normalized_objp[:, :-1]
            normalized_imp = normalized_imp[:, :-1]

            ret_correspondences.append((imp, objp, normalized_imp, normalized_objp, N_u, N_x, N_u_inv, N_x_inv))

        return ret_correspondences

    def minimizer_func(initial_guess, X, Y, h, N):
        """
        :param initial_guess:
        :param X:  normalized object points flattened
        :param Y:  normalized image points flattened
        :param h:  homography flattened
        :param N:  number of points
        :return:
        """

        x_j = X.reshape(N, 2)
        # Y = Y.reshape(N, 2)
        # h = h.reshape(3, 3)

        projected = [0 for i in range(2 * N)]
        for j in range(N):
            x, y = x_j[j]
            w = h[6] * x + h[7] * y + h[8]

            projected[2 * j] = (h[0] * x + h[1] * y + h[2]) / w
            projected[2 * j + 1] = (h[3] * x + h[4] * y + h[5]) / w

        return (np.abs(projected - Y)) ** 2

    def jac_function(initial_guess, X, Y, h, N):
        x_j = X.reshape(N, 2)
        jacobian = np.zeros((2 * N, 9), np.float64)
        for j in range(N):
            x, y = x_j[j]
            sx = np.float64(h[0] * x + h[1] * y + h[2])
            sy = np.float64(h[3] * x + h[4] * y + h[5])
            w = np.float64(h[6] * x + h[7] * y + h[8])
            jacobian[2 * j] = np.array([x / w, y / w, 1 / w, 0, 0, 0, -sx * x / w ** 2, -sx * y / w ** 2, -sx / w ** 2])
            jacobian[2 * j + 1] = np.array(
                [0, 0, 0, x / w, y / w, 1 / w, -sy * x / w ** 2, -sy * y / w ** 2, -sy / w ** 2])

        return jacobian

    def refine_homographies(H, correspondence, skip=False):
        if skip:
            return H

        image_points = correspondence[0]
        object_points = correspondence[1]
        normalized_image_points = correspondence[2]
        normalized_object_points = correspondence[3]
        N_u = correspondence[4]
        N_x = correspondence[5]
        N_u_inv = correspondence[6]
        N_x_inv = correspondence[7]

        N = normalized_object_points.shape[0]
        X = object_points.flatten()
        Y = image_points.flatten()
        h = H.flatten()
        h_prime = opt.least_squares(fun=minimizer_func, x0=h, jac=jac_function, method="lm", args=[X, Y, h, N],
                                    verbose=0)

        if h_prime.success:
            H = h_prime.x.reshape(3, 3)
        H = H / H[2, 2]
        return H

    def get_intrinsic_parameters(H_r):
        M = len(H_r)
        V = np.zeros((2 * M, 6), np.float64)

        def v_pq(p, q, H):
            v = np.array([
                H[0, p] * H[0, q],
                H[0, p] * H[1, q] + H[1, p] * H[0, q],
                H[1, p] * H[1, q],
                H[2, p] * H[0, q] + H[0, p] * H[2, q],
                H[2, p] * H[1, q] + H[1, p] * H[2, q],
                H[2, p] * H[2, q]
            ])
            return v

        for i in range(M):
            H = H_r[i]
            V[2 * i] = v_pq(p=0, q=1, H=H)
            V[2 * i + 1] = np.subtract(v_pq(p=0, q=0, H=H), v_pq(p=1, q=1, H=H))

        # solve V.b = 0
        u, s, vh = np.linalg.svd(V)
        b = vh[np.argmin(s)]

        # according to Zhang's method
        vc = (b[1] * b[3] - b[0] * b[4]) / (b[0] * b[2] - b[1] ** 2)
        l = b[5] - (b[3] ** 2 + vc * (b[1] * b[2] - b[0] * b[4])) / b[0]
        alpha = np.sqrt((l / b[0]))
        beta = np.sqrt(((l * b[0]) / (b[0] * b[2] - b[1] ** 2)))
        gamma = -1 * ((b[1]) * (alpha ** 2) * (beta / l))
        uc = (gamma * vc / beta) - (b[3] * (alpha ** 2) / l)

        print([vc,
               l,
               alpha,
               beta,
               gamma,
               uc])

        A = np.array([
            [alpha, gamma, uc],
            [0, beta, vc],
            [0, 0, 1.0],
        ])
        print("Intrinsic Camera Matrix is :")
        print(A)
        return A

    chessboard_correspondences = getChessboardCorners(images=None, visualize=True, num_images=num_images)

    chessboard_correspondences_normalized = normalize_points(chessboard_correspondences)

    print("M = ", len(chessboard_correspondences_normalized), " view images")
    print("N = ", len(chessboard_correspondences_normalized[0][0]), " points per image")

    H = []
    for correspondence in chessboard_correspondences_normalized:
        H.append(compute_view_based_homography(correspondence, reproj=False))

    H_r = []
    for i in range(len(H)):
        h_opt = refine_homographies(H[i], chessboard_correspondences_normalized[i], skip=False)
        H_r.append(h_opt)

    A = get_intrinsic_parameters(H_r)

    # print results
    string_intrinsic = "The intrinsic camera matrix is: \n {}".format(A)
    st.text(string_intrinsic)
    st.text("where ")
    st.latex(r'A = \begin {pmatrix} fs_x & fs_{\theta} & u_c \\ 0 & fs_y & v_c \\ 0 & 0 & 1 \end {pmatrix} ='
             r'\begin {pmatrix} \alpha & \gamma & u_c \\ 0 & \beta & v_c \\ 0 & 0 & 1 \end {pmatrix}')
    st.text("where alpha and beta are scale factor in image u and v axes and gamma describes the skew.")

    st.text("Once the intrinsic parameters are known, the extrinsic parameters can be calculated for each\n"
            "image (view) using the corresponding homography, H.")


if __name__ == "__main__":
    main()
