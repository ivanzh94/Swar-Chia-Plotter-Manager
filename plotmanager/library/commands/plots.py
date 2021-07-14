def create(size, memory_buffer, temporary_directory, destination_directory, threads, buckets, bitfield,
           chia_location='chia', temporary2_directory=None, farmer_public_key=None, pool_public_key=None,
           pool_contract_address=None, thread_multiplier_for_p2=None, exclude_final_directory=False):
    # modified
    flags = dict(
        # k=size,
        # b=memory_buffer,
        t=temporary_directory,
        d=destination_directory,
        r=threads,
        u=buckets,
    )
    if temporary2_directory is not None:
        flags['2'] = temporary2_directory
    if farmer_public_key is not None:
        flags['f'] = farmer_public_key
    if pool_public_key is not None and pool_contract_address is None:
        flags['p'] = pool_public_key
    if pool_contract_address is not None:
        flags['c'] = pool_contract_address
    if thread_multiplier_for_p2 is not None:
        flags['K'] = thread_multiplier_for_p2
    # if bitfield is False:
    #     flags['e'] = ''
    # if exclude_final_directory:
    #     flags['x'] = ''

    data = [chia_location, '-n', '1']
    for key, value in flags.items():
        flag = f'-{key}'
        data.append(flag)
        if value == '':
            continue
        data.append(str(value))
    return data
