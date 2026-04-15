import './editProfile.scss';
import { Input, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useUser } from '@/contexts/UserContext';
import { getUserInfo, updateUserInfo } from '@/api/loginapi';
import { BRAND_ICON_URL } from '@/constants/brand';
import { UserInfo } from '@/models/LoginModels';
import AppButton from '@/shared/ui/button/button';
import { selectFileWeb } from '@/utils/file';
import { PhoneIcon, UserIcon } from '@/shared/ui/icon';

export default function EditProfile() {
  const defaultAvatar = BRAND_ICON_URL;
  const [avatar, setAvatar] = useState(defaultAvatar)
  const { setUserInfo, refresh } = useUser()

  const [info, setInfo] = useState<UserInfo>()
  useEffect(() => {
    getUserInfo().then((res: UserInfo) => {
      setUserInfo(res)
      setInfo(res)
      setAvatar(res.avatar || defaultAvatar)
    })
  }, [defaultAvatar, setUserInfo])

  const isSaveDisabled = useMemo(() => {
    if (!info?.name?.trim()) return true
    if (!info?.phone?.trim()) return true
    return false
  }, [info])

  // 保存  
  const saveUserInfo = () => {    
    if (!info) return
    if(info?.phone?.trim().length !== 11 || !/^1[3456789]\d{9}$/.test(info.phone.trim())) {
      message.error('手机号格式错误')
      return
    }    
    updateUserInfo(info).then(() => {
      message.success('保存成功')
      refresh()
    }).catch(() => {
      message.error('更新失败')
    })
  }

  return (
    <div className="edit-profile">
      <div className="flex items-center justify-center">
        <img
          onClick={() => selectFileWeb(["image/*"]).then((url) => {
            if (url) {
              setInfo((prev) => (prev ? { ...prev, avatar: url } : prev))
              setAvatar(url)
            }
          })}
          className="size-[80px] rounded-full"
          src={avatar}
          alt="头像"
        />
      </div>
      <div className="field">
        <div className="label">昵称</div>
        <Input
          value={info?.name}
          size="large"
          maxLength={15}
          placeholder="输入昵称"
          rootClassName="app-input-root"
          prefix={<UserIcon className="icon profile-edit-icons app-icon" />}
          onChange={(e) => setInfo((prev) => (prev ? { ...prev, name: e.target.value } : prev))}
        />
      </div>

      <div className="field">
        <div className="label">手机号</div>
        <Input
          value={info?.phone}
          size="large"
          disabled={true}
          placeholder="输入手机号"
          rootClassName="app-input-root"
          prefix={<PhoneIcon className="icon profile-edit-icons app-icon" />}
          onChange={(e) => setInfo((prev) => (prev ? { ...prev, phone: e.target.value } : prev))}
        />
      </div>
      <AppButton variant="primary" disabled={isSaveDisabled} onClick={saveUserInfo}>保存</AppButton>
    </div>
  );
}
