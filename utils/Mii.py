from binascii import hexlify, unhexlify
from bitstring import BitArray
from struct import pack


#general purpose mii class
class Mii:
	def __init__(self, data):
		data = bytearray(data)
		bits = BitArray(data)
		genderMap = {False:"Male", True:"Female"}
		colorMap = {0:'Red', 1:'Orange', 2:'Yellow', 3:'Light Green', 4:'Dark Green', 5:'Dark Blue', 6:'Light Blue', 7:'Pink', 8:'Purple', 9:'Brown', 10:'White', 11:'Black'}
		self.gender = genderMap[bits[1]]
		self.isGirl = bits[1]
		if bits[2:6].uint == 0:
			self.birthdaySet = False
			self.birthMonth = None
			self.birthDay = None
		else:
			self.birthdaySet = True
			self.birthMonth = bits[2:6].uint
			self.birthDay = bits[6:11].uint
		self.shirtColorVerbose = colorMap[bits[11:15].uint]
		self.shirtColor = bits[11:15].uint
		self.isFavorite = bits[16]
		miiName = data[2:22].decode(u"utf-16be").strip('\x00')
		self.miiName, _, _ = miiName.partition('\x00')
		self.bodyHeight = int.from_bytes(data[22:23], 'big')
		self.bodyWeight = int.from_bytes(data[23:24], 'big')
		self.avatarId = hexlify(data[24:28])
		self.clientId = hexlify(data[28:32])
		self.faceType = bits[256:259].uint
		self.faceColor = bits[259:262].uint
		self.facialFeature = bits[262:266].uint
		self.unknown1 = bits[266:269].uint
		self.doesMingle = bits[269]
		self.unknown2 = bits[270]
		self.downloaded = bits[271]
		self.hairType = bits[272:279].uint
		self.hairColor = bits[279:282].uint
		self.hairFlipped = bits[282]
		self.unknown3 = bits[283:288].uint
		self.eyebrowType = bits[288:293].uint
		self.unknown4 = bits[293]
		self.eyebrowRotation = bits[294:298].uint
		self.unknown5 = bits[298:304].uint
		self.eyebrowColor = bits[304:307].uint
		self.eyebrowSize = bits[307:311].uint
		self.eyebrowVertical = bits[311:316].uint
		self.eyebrowHorizontal = bits[316:320].uint
		self.eyeType = bits[320:326].uint
		self.unknown6 = bits[326:328].uint
		self.eyeRotation = bits[328:331].uint
		self.eyeVertical = bits[331:336].uint
		self.eyeColor = bits[336:339].uint
		self.unknown7 = bits[339]
		self.eyeSize = bits[340:343].uint
		self.eyeHorizontal = bits[343:347].uint
		self.unknown8 = bits[347:352].uint
		self.noseType = bits[352:356].uint
		self.noseSize = bits[356:360].uint
		self.noseVertical = bits[360:365].uint
		self.unknown9 = bits[365:368].uint
		self.mouthType = bits[368:373].uint
		self.mouthColor = bits[373:375].uint
		self.mouthSize = bits[375:379].uint
		self.mouthVertical = bits[379:384].uint
		self.glassesType = bits[384:388].uint
		self.glassesColor = bits[388:391].uint
		self.unknown10 = bits[391]
		self.glassesSize = bits[392:395].uint
		self.glassesVertical = bits[395:400].uint
		self.facialHairMustache = bits[400:402].uint
		self.facialHairBeard = bits[402:404].uint
		self.facialHairColor = bits[404:407].uint
		self.facialHairSize = bits[407:411].uint
		self.facialHairVertical = bits[411:416].uint
		self.hasMole = bits[416]
		self.moleSize = bits[417:421].uint
		self.moleVertical = bits[421:426].uint
		self.moleHorizontal = bits[426:431].uint
		self.unknown11 = bits[431]
		creatorName = data[54:74].decode(u"utf-16be").strip('\x00')
		self.creatorName, _, _ = creatorName.partition('\x00')


#rendering miis

def renderMii(miiData:Mii, renderType='face', imageWidth: int=512, angles: int=1, xRot: int=0, yRot: int=0, zRot: int=0): #returns an image link to the rendered mii
	#credit to riiconnect24 for the original function. I rewrote it with camelCase and my own mii class.
	if renderType not in ['face', 'all_body']:
		raise Exception("Not a valid renderType. Valid renderTypes are 'face' and 'all_body'.")
	if imageWidth not in [512, 270, 140, 128, 96]:
		raise Exception("Argument imageWidth must be 512, 270, 140, 128, or 96, otherwise rendering server will not work.")
	if angles not in range(16) and angles != 0:
		raise Exception("Range of angles is 1-16. Please change it.")

	studio_mii = {}
	makeup = {1: 1, 2: 6, 3: 9, 9: 10}
	wrinkles = {4: 5, 5: 2, 6: 3, 7: 7, 8: 8, 10: 9, 11: 11}
	#map original mii datapoints into mii studio ones

	if miiData.facialHairColor == 0:
		studio_mii["facial_hair_color"] = 8
	else:
		studio_mii["facial_hair_color"] = miiData.facialHairColor
	studio_mii["beard_goatee"] = miiData.facialHairBeard
	studio_mii["body_weight"] = miiData.bodyWeight
	studio_mii["eye_stretch"] = 3
	studio_mii["eye_color"] = miiData.eyeColor + 8
	studio_mii["eye_rotation"] = miiData.eyeRotation
	studio_mii["eye_size"] = miiData.eyeSize
	studio_mii["eye_type"] = miiData.eyeType
	studio_mii["eye_horizontal"] = miiData.eyeHorizontal
	studio_mii["eye_vertical"] = miiData.eyeVertical
	studio_mii["eyebrow_stretch"] = 3
	if miiData.eyebrowColor == 0:
		studio_mii["eyebrow_color"] = 8
	else:
		studio_mii["eyebrow_color"] = miiData.eyebrowColor
	studio_mii["eyebrow_rotation"] = miiData.eyebrowRotation
	studio_mii["eyebrow_size"] = miiData.eyebrowSize
	studio_mii["eyebrow_type"] = miiData.eyebrowType
	studio_mii["eyebrow_horizontal"] = miiData.eyebrowHorizontal
	studio_mii["eyebrow_vertical"] = miiData.eyebrowVertical
	studio_mii["face_color"] = miiData.faceColor
	if miiData.facialFeature in makeup:
		studio_mii["face_makeup"] = makeup[miiData.facialFeature]
	else:
		studio_mii["face_makeup"] = 0
	studio_mii["face_type"] = miiData.faceType
	if miiData.facialFeature in wrinkles:
		studio_mii["face_wrinkles"] = wrinkles[miiData.facialFeature]
	else:
		studio_mii["face_wrinkles"] = 0
	studio_mii["favorite_color"] = miiData.shirtColor
	studio_mii["gender"] = miiData.isGirl
	if miiData.glassesColor == 0:
		studio_mii["glasses_color"] = 8
	elif miiData.glassesColor < 6:
		studio_mii["glasses_color"] = miiData.glassesColor + 13
	else:
		studio_mii["glasses_color"] = 0
	studio_mii["glasses_size"] = miiData.glassesSize
	studio_mii["glasses_type"] = miiData.glassesType
	studio_mii["glasses_vertical"] = miiData.glassesVertical
	if miiData.hairColor == 0:
		studio_mii["hair_color"] = 8
	else:
		studio_mii["hair_color"] = miiData.hairColor
	studio_mii["hair_flip"] = miiData.hairFlipped
	studio_mii["hair_type"] = miiData.hairType
	studio_mii["body_height"] = miiData.bodyHeight
	studio_mii["mole_size"] = miiData.moleSize
	studio_mii["mole_enable"] = miiData.hasMole
	studio_mii["mole_horizontal"] = miiData.moleHorizontal
	studio_mii["mole_vertical"] = miiData.moleVertical
	studio_mii["mouth_stretch"] = 3
	if miiData.mouthColor < 4:
		studio_mii["mouth_color"] = miiData.mouthColor + 19
	else:
		studio_mii["mouth_color"] = 0
	studio_mii["mouth_size"] = miiData.mouthSize
	studio_mii["mouth_type"] = miiData.mouthType
	studio_mii["mouth_vertical"] = miiData.mouthVertical
	studio_mii["beard_size"] = miiData.facialHairSize
	studio_mii["beard_mustache"] = miiData.facialHairMustache
	studio_mii["beard_vertical"] = miiData.facialHairVertical
	studio_mii["nose_size"] = miiData.noseSize
	studio_mii["nose_type"] = miiData.noseType
	studio_mii["nose_vertical"] = miiData.noseVertical

	data = b""
	n = r = 256
	miiDict = studio_mii.values()
	data += hexlify(pack(">B", 0))
	for v in miiDict:
		eo = (7 + (v ^ n)) % 256
		n = eo
		data += hexlify(pack(">B", eo))

	url = "https://studio.mii.nintendo.com/miis/image.png?data=" + data.decode("utf-8") + f'&type={renderType}&width={imageWidth}'

	if xRot or yRot or zRot != 0:
		url += f'&characterXRotate={xRot}&characterYRotate={yRot}&characterZRotate={zRot}'

	if angles != 1:
		url += f'&instanceCount={angles}'

	return url